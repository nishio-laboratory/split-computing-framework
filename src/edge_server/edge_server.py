#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import base64
import json
import os
import socket
import sys
import threading
import time

import numpy as np
from PIL import Image

from src.conf import environment_settings
from src.lib import code, command, inference, save_result
from src.lib.logger import create_logger
from src.lib.model.request import (
    CommonRequest,
    EdgeServerInferenceResultRequest,
    EdgeServerReceivedResultRequest,
    IotDeviceResultDataRequest,
    IotDeviceResultSummaryRequest,
    CloudServerSettingRequest,
    ProcessTimeRequest
)
from src.lib.model.response import CommonResponse
from src.lib import compressor
from src.lib.tc import Tc

BUFFER_NPYFILE = os.path.join(os.path.dirname(__file__), "buffer.npy")
BUFFER_JPGFILE = os.path.join(os.path.dirname(__file__), "buffer.jpg")

class EdgeServer:
    def __init__(self):
        self.command_list = {
            command.IOT_SEND_RESULT_SUMMARY: self.process_iot_send_result_summary,
            command.IOT_SEND_RESULT_DATA: self.process_iot_send_result_data,
            command.CLOUD_SEND_SETTING_TO_EDGE: self.process_cloud_send_setting
        }
        self.logger = create_logger(__name__)
        self.is_wait = True
        self.latest_received_time = None
        self.setting = None
        self.compressor = compressor.Compressor()

        # 一回だけ推論モデルのロードを行うためのフラグ
        self.already_load_model = False
        self.total_received_data_size = 0

        # 推論を一回だけ行うためのフラグ
        # これがないと、推論を行なった後でも、新たなパケットを受信するたびに推論を繰り返してしまう
        # 1つの推論対象に対する推論が完了したらTrueにし、新たな推論対象のresult_summaryを受信したらFalseに戻す
        self.inference_completed = False
        self.retry_count = 0
        self.has_network_error = False

    def main(self):
        try:
            self.receive_common_request()
        except KeyboardInterrupt:
            Tc.reset_tc(
                environment_settings.EDGE_NETWORK_DEVICE,
                self.setting['edge_network_delay_time'],
                self.setting['edge_network_dispersion_time'],
                self.setting['edge_network_loss_rate'],
                self.setting['edge_network_band_limitation']
            )

    def command_not_found(self, request):
        raise Exception("command not found")
    
    def process_cloud_send_setting(self, request):
        """
        クラウドサーバーから受信した設定を処理する
        """
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.setting = json.loads(request.setting)
        self.logger.info("====== get {}======".format(self.setting))
        self.target_image_sequence_number = 0 #cloudから設定を受け取るたびにリセットする推論対象のシーケンス番号

        payload = ""  # 正常に受信できた場合は、「共通レスポンスデータ」のpayloadを空文字列を格納する。
        response = CommonResponse(code.SUCCESS, request.request_id, "", payload)

        # クラウドサーバー側のUDPのタイムアウト時間は、data waiting timeより長くしておかないといけない
        # data waiting timeの間にudpソケットがタイムアウトしてしまったら困るので、5秒分だけ長くしておく
        waiting_time_seconds = self.setting['waiting_time'] / 1000.0
        timeout_seconds = waiting_time_seconds + 5
        self.udp_socket.settimeout(timeout_seconds)

        Tc.execute_tc(
            environment_settings.EDGE_NETWORK_DEVICE,
            self.setting['edge_network_delay_time'],
            self.setting['edge_network_dispersion_time'],
            self.setting['edge_network_loss_rate'],
            self.setting['edge_network_band_limitation']
        )
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return response   

    def process_iot_send_result_summary(self, request):
        """
        IoTデバイスから受信したresult_summaryを処理する
        """
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        self.latest_received_time = time.time()

        self.iot_result_summary = request

        self.filename = self.iot_result_summary.filename

        if self.setting['layer'] == 0:
            self.iot_result_data = b""
        else:
            self.iot_result_data = np.zeros(self.iot_result_summary.num_elements)
            if self.setting['split_mode'] == 'random':
                # IoTデバイス側と同じシード値を使っているためIoTデバイス側と同じシャッフル列が生成され、ランダム順のパケットを元の順番に並べ直せる。
                # np.random.seed(environment_settings.IOT_RANDOM_SEED_SHUFFLE)
                # 結局同じことだが、受信したランダムシードを用いる方が正しいのでは？
                np.random.seed(self.iot_result_summary.random_seed)
                self.k = np.random.permutation(self.iot_result_summary.num_elements)
            elif self.setting['split_mode'] == 'sequential':
                self.k = np.arange(self.iot_result_summary.num_elements)
            else:
                raise Exception('IOT_SPLIT_MODE has invalid value.')

        self.iot_result_data_received_packets = 0
        self.iot_result_data_received_elements = 0
        payload = ""  # 正常に受信できた場合は、「共通レスポンスデータ」のpayloadを空文字列を格納する。
        self.logger.info(f"IotResultSummary : {request}")
        response = CommonResponse(code.SUCCESS, request.request_id, "", payload)

        self.inference_completed = False
        self.thread_timer = threading.Thread(target=self.reception_timer)
        self.thread_timer.setDaemon(True)
        self.thread_timer.start()

        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return response

    def reception_timer(self):
        """
        result_summaryやresult_dataを受信した時に更新されるself.latest_received_timeと
        現在時刻を比較することで経過時間を測定し、GUIで設定したdata_waiting_timeを超えたら
        IoTデバイスに時間経過したことを表すレスポンスを送信し、推論処理に移る
        """
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        # self.latest_received_timeは、process_iot_send_result_dataでも更新される

        while self.latest_received_time is not None:
            # 経過時間
            elapsed_time = time.time() - self.latest_received_time
            self.logger.debug(f"Elapsed time : {elapsed_time}")

            # GUIで設定されたwaiting_time(ms)以上経過した場合
            if (self.setting['waiting_time'] / 1000.0 <= elapsed_time):
                self.send_received_result("failure")
                # 十分な受信率を達成していない場合でも、設定した待機時間経過により推論を開始する
                if not self.inference_completed:
                    transmission_end_time = time.time()
                    save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Transmission end time = {:.9f}".format(self.target_image_sequence_number, transmission_end_time) + '\n', mode='a')
                    self.send_received_result("success")
                    save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Data Size = {} bytes".format(self.target_image_sequence_number, self.total_received_data_size) + '\n', mode='a')
                    save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Packets = {}".format(self.target_image_sequence_number, self.iot_result_data_received_packets) + '\n', mode='a')
                    self.do_inference()
                break
            time.sleep(0.1)

        self.latest_received_time = None
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def process_iot_send_result_data(self, request):
        '''
        IoTデバイスから受信したresult_dataを処理する
        '''
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        self.latest_received_time = time.time()

        # 受信したパケットの数
        self.iot_result_data_received_packets += 1
        # パケットの受信率
        packets_receive_rate = self.iot_result_data_received_packets / self.iot_result_summary.num_packets

        self.logger.info(f"{request.sequence}th packet was received.")
        self.logger.info(
            f"{self.iot_result_data_received_packets} of {self.iot_result_summary.num_packets} packets ({packets_receive_rate * 100} %) received."
        )
        self.total_received_data_size += len(request.payload)
        payload = request.payload.encode()
        # 全てエッジで推論する場合
        if self.setting['layer'] == 0:
            self.iot_result_data_received_elements += len(payload)
            elements_receive_rate = self.iot_result_data_received_elements / self.iot_result_summary.num_elements
            self.logger.info(
                f"{self.iot_result_data_received_elements} of {self.iot_result_summary.num_elements} elements ({elements_receive_rate * 100} %) received."
            )
            self.iot_result_data += base64.b64decode(payload)
            if (
                self.iot_result_data_received_elements == self.iot_result_summary.num_elements
                and not self.inference_completed
            ):
                with open(BUFFER_JPGFILE, "wb") as f:
                    f.write(self.iot_result_data)
                self.iot_result_data = np.array(Image.open(BUFFER_JPGFILE))
                transmission_end_time = time.time()
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Transmission end time = {:.9f}".format(self.target_image_sequence_number, transmission_end_time) + '\n', mode='a')
                self.send_received_result("success")
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Data Size = {} bytes".format(self.target_image_sequence_number, self.total_received_data_size) + '\n', mode='a')
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Packets = {}".format(self.target_image_sequence_number, self.iot_result_data_received_packets) + '\n', mode='a')
                self.total_received_data_size = 0
                self.do_inference()
        else:
            with open(BUFFER_NPYFILE, "wb") as f:
                f.write(base64.b64decode(payload))
            payload = np.load(BUFFER_NPYFILE)
            self.iot_result_data_received_elements += len(payload)
            elements_receive_rate = self.iot_result_data_received_elements / self.iot_result_summary.num_elements
            self.logger.info(
                f"{self.iot_result_data_received_elements} of {self.iot_result_summary.num_elements} elements ({elements_receive_rate * 100} %) received."
            )
            os.remove(BUFFER_NPYFILE)

            for i in range(len(payload)):
                self.iot_result_data[
                    self.k[request.sequence * environment_settings.IOT_SPLITTED_NUMPY_LENGTH + i]
                ] = payload[i]

            if (self.setting['reach_rate'] <= elements_receive_rate and not self.inference_completed):
                print(self.iot_result_data)
                transmission_end_time = time.time()
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Transmission end time = {:.9f}".format(self.target_image_sequence_number, transmission_end_time) + '\n', mode='a')
                self.send_received_result("success")
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Data Size = {} bytes".format(self.target_image_sequence_number, self.total_received_data_size) + '\n', mode='a')
                save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Received Packets = {}".format(self.target_image_sequence_number, self.iot_result_data_received_packets) + '\n', mode='a')
                self.total_received_data_size = 0

                self.do_inference()

        payload = ""  # 正常に受信できた場合は、「共通レスポンスデータ」のpayloadを空文字列を格納する。
        response = CommonResponse(code.SUCCESS, request.request_id, "", payload)

        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return response

    def do_inference(self):
        #self.send_process_time("edge:do_inference:start:{}".format(self.filename)) # 実行時間短縮のためコメントアウト中
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        self.logger.info("compression attribute [PCA_rate] = {}, [Qubit_type] = {}".format(self.setting['PCA_rate'], self.setting['Qubit_type']))
        if self.setting['Qubit_type'] != compressor.Compressor.QUBIT_NON_COMPRESSION:
            if self.setting['Qubit_type'] == compressor.Compressor.QUBIT_16BIT_INT:
                self.iot_result_data = self.compressor.extract_nparray_16bit_int(self.iot_result_data)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_8BIT_INT:
                self.iot_result_data = self.compressor.extract_nparray_8bit_int(self.iot_result_data)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_NORMALIZE_16BIT_INT:
                self.iot_result_data = self.compressor.extract_nparray_16bit_int(self.iot_result_data)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_NORMALIZE2SIGMA_16BIT_INT:
                self.iot_result_data = self.compressor.extract_nparray_16bit_int(self.iot_result_data)
        else:
            self.iot_result_data = self.iot_result_data

        self.logger.info('print extracted qubit compression')
        self.logger.info(self.iot_result_data)

        if self.setting['PCA_rate'] != 0 and self.setting['PCA_rate'] != 1.0:
            self.iot_result_data = self.compressor.extract_pca(self.iot_result_data, self.setting['model'], self.setting['layer'])

        if self.setting['reload']:
            self.model = inference.load_model(self.setting['model'])
        else:
            if not self.already_load_model:
                self.model = inference.load_model(self.setting['model'])
                self.already_load_model = True
        
        self.model_input_shape = (1,) + self.model.layers[self.setting['layer']].input_shape[
            1:
        ]
        self.logger.info(f"Edge model input shape : {self.model_input_shape}")

        # NOTE: この処理を通さずにいると float64 として認識されてしまうため、float32に変更する処理を行う
        inter_test_decomp = self.iot_result_data
        inter_test_decomp = inference.decompression_16_to_32(inter_test_decomp)
        inter_test_decomp = inter_test_decomp.reshape(self.model_input_shape)

        np.save("./data/sample_edge.npy", inter_test_decomp)
        inference_start_time = time.time()
        save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Edge processing start time = {:.9f}".format(self.target_image_sequence_number, inference_start_time) + '\n', mode='a')
        inference_on_edge = inference.InferenceStartEndLayer(
            self.model, self.setting['layer'] + 1, len(self.model.layers), inter_test_decomp
        )
        y_pred = inference_on_edge.inference()
        inference_end_time = time.time()
        save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Edge processing end time = {:.9f}".format(self.target_image_sequence_number, inference_end_time) + '\n', mode='a')
        self.target_image_sequence_number += 1
        self.edge_result_data = y_pred[0].argmax(axis=0)
        self.logger.info(f"Pred : {self.edge_result_data}")
        # self.send_process_time("edge:do_inference:end:{}".format(self.filename))

        # 推論を行なったことを表すフラグを立てる
        self.inference_completed = True

        while self.send_edge_inference_result() is False and self.retry_count < environment_settings.MAX_RETRY_COUNT:
            self.retry_count += 1
            self.logger.info(f"retry count is {self.retry_count}")
        if environment_settings.MAX_RETRY_COUNT <= self.retry_count:
            self.logger.error("max retry count is over...")
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def get_setting_from_cloud_server(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
        req = CommonRequest(command.EDGE_GET_SETTING)
        self.logger.debug(f"Request JSON : {req.get_json()}")
        sock.send(req.get_json().encode("ascii"))

        rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
        self.logger.debug(f"Response JSON : {response.get_json()}")
        self.logger.debug(f"Response payload : {response.payload}")
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

        self.setting = response

    def send_received_result(self, mode):
        """
        mode == "success"が指定された場合はIoTデバイスに十分なデータが届いたことを表すレスポンスを送信し、
        mode == "failure"が指定された場合はIoTデバイスに待機時間が超過したことを表すレスポンスを送信する
        """
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.latest_received_time = None

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.IOT_HOSTNAME, environment_settings.IOT_PORT))

        if mode == "success":
            req = EdgeServerReceivedResultRequest(
                command.EDGE_SEND_RECEIVED_RESULT, code.SUFFICIENT_DATA_ARRIVAL
            )
        elif mode == "failure":
            req = EdgeServerReceivedResultRequest(
                command.EDGE_SEND_RECEIVED_RESULT, code.TIME_EXCEEDED
            )
        else:
            raise Exception(f"No mode matched {mode}")

        self.logger.debug(f"Request JSON : {req.get_json()}")
        sock.send(req.get_json().encode("ascii"))

        rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
        self.logger.debug(f"Response JSON : {response.get_json()}")
        self.logger.debug(f"Response payload {response.payload}")
        assert response.payload == ""

        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def send_edge_inference_result(self):
        """
        エッジサーバーでの推論結果をクラウドサーバーに送信する
        """
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
            req = EdgeServerInferenceResultRequest(
                command.EDGE_SEND_INFERENCE_RESULT, str(self.edge_result_data), self.filename
            )
            self.logger.debug(f"Request JSON : {req.get_json()}")
            sock.send(req.get_json().encode("ascii"))

            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
            response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
            self.logger.debug(f"Response JSON : {response.get_json()}")
            self.logger.debug(f"Response payload : {response.payload}")
        except socket.error as se:
            self.has_network_error = True
            self.logger.exception(se)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False       
        except Exception as e:
            self.has_network_error = True
            self.logger.exception(e)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def receive_common_request(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        # TCPソケット、およびUDPソケットが待機状態にあることを表すフラグ
        # TCPソケットが終了コマンドを受け取るとFalseになる
        self.is_wait = True

        # TCPソケットとUDPソケットの作成を並列処理するためのスレッド
        tcp_thread = threading.Thread(target=self.receive_tcp_requests)
        udp_thread = threading.Thread(target=self.receive_udp_requests)

        # TCPソケットとUDPソケットを開くためのスレッドを開始
        tcp_thread.start()
        udp_thread.start()
        
        self.logger.info("wait thread process")
        # スレッドの終了を待つ
        tcp_thread.join()
        self.logger.info("joined tcp_thread")
        udp_thread.join()
        self.logger.info("joined udp_thread")

        # ソケットを閉じる
        if self.tcp_socket:
            self.tcp_socket.close()
            self.logger.debug("close tcp socket")
        if self.udp_socket:
            self.udp_socket.close()
            self.logger.debug("close udp socket")

        if self.setting is not None:
            Tc.reset_tc(
                environment_settings.EDGE_NETWORK_DEVICE,
                self.setting['edge_network_delay_time'],
                self.setting['edge_network_dispersion_time'],
                self.setting['edge_network_loss_rate'],
                self.setting['edge_network_band_limitation']
            )
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def receive_tcp_requests(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        # TCPソケットの受信処理

        try:
            # TCPソケットの作成
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_PORT))
            self.tcp_socket.listen(5)
            while self.is_wait and self.retry_count < environment_settings.MAX_RETRY_COUNT:
                self.logger.info('wait receive...')
                conn, addr = self.tcp_socket.accept()
                data = conn.recv(environment_settings.BUFFER_SIZE)
                self.logger.debug(f"Request data : {data}")
                self.logger.debug(f"Request addr : {addr}")
                converted_req = CommonRequest.convert_from_json(data)
                self.logger.debug(f"Request JSON : {converted_req.get_json()}")

                # 終了コマンドは個別で処理する
                if converted_req.command == command.EDGE_END:
                    res = CommonResponse(code.SUCCESS, converted_req.request_id, "", "")
                    conn.sendall(res.get_json().encode())
                    conn.close()
                    self.is_wait = False
                    break

                if converted_req.command in self.command_list:
                    if converted_req.command == command.IOT_SEND_RESULT_SUMMARY:
                        converted_req = IotDeviceResultSummaryRequest.convert_from_json(
                            data
                        )
                    elif converted_req.command == command.IOT_SEND_RESULT_DATA:
                        converted_req = IotDeviceResultDataRequest.convert_from_json(
                            data
                        )
                    elif converted_req.command == command.CLOUD_SEND_SETTING_TO_EDGE:
                        converted_req = (
                            CloudServerSettingRequest.convert_from_json(data)
                        )
                    res = self.command_list[converted_req.command](converted_req)
                    conn.sendall(res.get_json().encode())

            conn.close()
        except socket.timeout as st:
            self.has_network_error = True
            self.logger.exception(st)
            return False
        except Exception as e:
            self.has_network_error = True
            self.logger.exception(e)
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def receive_udp_requests(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        # UDPソケットの受信処理
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_UDP_PORT))
            '''
            受信した終了コマンドでこのスレッドを終了させるために、タイムアウトを設定
            パケットの受信待機時間にudpソケットがタイムアウトしてしまったら困るので、GUIで設定したdata_waiting_timeより5秒分だけ長くしておきたい
            しかし最初はまだdata_waiting_timeの設定値を受信していないので、とりあえず5秒で初期化しておく
            '''
            initial_timeout_seconds = 5
            self.udp_socket.settimeout(initial_timeout_seconds)  # タイムアウトを5秒に設定

            while self.is_wait and self.has_network_error is False: # TCPソケット側が終了コマンドを受信していない間繰り返す
                try:
                    data, addr = self.udp_socket.recvfrom(environment_settings.BUFFER_SIZE)
                except socket.timeout:
                    self.logger.debug(f"UDP timeout")
                    continue

                self.logger.debug(f"UDP Request data : {data}")
                self.logger.debug(f"UDP Request addr : {addr}")
                converted_req = CommonRequest.convert_from_json(data)
                self.logger.debug(f"UDP Request JSON : {converted_req.get_json()}") 

                # 受信したconverted_reqの処理
                if converted_req.command in self.command_list:
                    # UDPで送信されてくる可能性があるコマンドはIOT_SEND_RESULT_DATAのみ
                    if converted_req.command == command.IOT_SEND_RESULT_DATA:
                        converted_req = IotDeviceResultDataRequest.convert_from_json(
                            data
                        )
                    res = self.command_list[converted_req.command](converted_req)
                    # UDPの場合はレスポンスを返さない
        except socket.timeout as st:
            self.logger.exception(st)
            return False
        except Exception as e:
            self.logger.exception(e)
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def send_process_time(self, process_name):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))

        request = ProcessTimeRequest(
            command.EDGE_SEND_PROCESS_TIME,
            process_name,
            time.time()
        )
        self.logger.debug(f"ProcessTimeRequest : {request.get_json()}")
        sock.send(request.get_json().encode("ascii"))

        rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        self.logger.debug(f"Received data : {rcv_data}")
        response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
        self.logger.debug(f"Response JSON : {response.get_json()}")
        self.logger.debug(f"Response payload : {response.payload}")
        assert response.payload == ""
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

if __name__ == "__main__":
    edge_server = EdgeServer()
    edge_server.main()
