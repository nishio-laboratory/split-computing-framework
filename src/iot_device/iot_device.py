#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import base64
import json
import math
from operator import ne
import os
import socket
import sys
import threading
import datetime
import time
import shutil
from PIL import Image

T_DELTA = datetime.timedelta(hours=9)

import numpy as np
from PIL import Image
from tensorflow.keras.datasets import mnist

from src.conf import environment_settings
from src.lib import code, command, inference, save_result
from src.lib.logger import create_logger
from src.lib.model.request import (
    CommonRequest,
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

class IotDevice:
    def __init__(self) -> None:
        self.command_list = {
            command.EDGE_SEND_RECEIVED_RESULT: self.process_send_received_result,
            command.CLOUD_SEND_SETTING_TO_IOT: self.process_cloud_send_setting,
        }
        self.logger = create_logger(__name__)
        self.terminate_sending_result_data_flag = True
        self.compressor = compressor.Compressor()

        # 一回だけ推論モデルのロードを行うためのフラグ
        self.already_load_model = False
        self.retry_count = 0

    def main(self):
        self.download_and_save_mnist_images()
        self.thread_receive = threading.Thread(target=self.receive_common_request)
        self.thread_receive.start()

    def set_dummy_result_data(self):
        self.result_data = np.random.randint(0, 255, (32, 32, 128))

    def do_inference(self):
        #self.send_process_time("iot:do_inference:start:{}".format(os.path.splitext(os.path.basename(self.process_target_image_file))[0])) # 実行時間短縮のためコメントアウト中
        """X_testをCNNの前半で処理し圧縮したものをself.result_dataに入れる"""

        if self.setting['reload']:
            self.model = inference.load_model(self.setting['model'])
        else:
            if not self.already_load_model:
                self.model = inference.load_model(self.setting['model'])
                self.already_load_model = True

        inference_start_time = time.time()
        save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, IoT processing start time = {:.9f}".format(self.target_image_sequence_number, inference_start_time) + '\n', mode='a')
        inference_on_IoTdevice = inference.InferenceStartEndLayer(self.model, 1, self.setting['layer'], np.expand_dims(self.process_target, axis=-1)) # 画像の入力サイズを(28, 28)から(28, 28, 1)にする必要がある
        inter_test  = inference_on_IoTdevice.inference()    #中間層出力を得る
        inference_end_time = time.time()
        save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, IoT processing end time = {:.9f}".format(self.target_image_sequence_number, inference_end_time) + '\n', mode='a')

        # NOTE: 2022/3版では16bit float圧縮を行っていたが、圧縮は選択式にしたため、コメントアウト
        # inter_test_comp = inference.compression_32_to_16(inter_test)    #圧縮
        inter_test_comp = None

        if self.setting['PCA_rate'] != 0 and self.setting['PCA_rate'] != 1.0:
            inter_test = self.compressor.compress_pca(inter_test, self.setting['PCA_rate'], self.setting['model'], self.setting['layer'])

        self.logger.info("compression attribute [PCA_rate] = {}, [Qubit_type] = {}".format(self.setting['PCA_rate'], self.setting['Qubit_type']))
        if self.setting['Qubit_type'] != compressor.Compressor.QUBIT_NON_COMPRESSION:
            if self.setting['Qubit_type'] == compressor.Compressor.QUBIT_16BIT_INT:
                inter_test_comp = self.compressor.compress_nparray_16bit_int(inter_test)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_8BIT_INT:
                inter_test_comp = self.compressor.compress_nparray_8bit_int(inter_test)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_NORMALIZE_16BIT_INT:
                inter_test_comp = self.compressor.compress_nparray_normalize_16bit_int(inter_test)
            elif self.setting['Qubit_type'] == compressor.Compressor.QUBIT_NORMALIZE2SIGMA_16BIT_INT:
                inter_test_comp = self.compressor.compress_nparray_normalize2sigma_16bit_int(inter_test)
        else:
            inter_test_comp = inter_test

        self.result_data = inter_test_comp
        np.save("./data/sample_iot.npy", self.result_data)
        save_result.save_inter_or_image(self.setting['current_time_str'], "middle_layers", self.target_image_sequence_number, self.result_data, is_inter=True)

        #self.send_process_time("iot:do_inference:end:{}".format(os.path.splitext(os.path.basename(self.process_target_image_file))[0])) # 実行時間短縮のためコメントアウト中

    def download_and_save_mnist_images(self, extensions=["png", "jpg"]):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        if os.path.exists("./data/mnist"):
            self.logger.info(f"MNIST data already exists.")
            return

        (X_train, y_train), (X_test, y_test) = mnist.load_data()

        for extension in extensions:
            os.makedirs(f"./data/mnist/X_train/{extension}", exist_ok=True)
            os.makedirs(f"./data/mnist/X_test/{extension}", exist_ok=True)

        for i, X in enumerate([X_train, X_test]):
            for j, numpy_image in enumerate(X):
                pil_image = Image.fromarray(numpy_image)

                for extension in extensions:
                    if i == 0:
                        image_filename = f"./data/mnist/X_train/{extension}/{str(j).zfill(5)}.{extension}"
                    elif i == 1:
                        image_filename = f"./data/mnist/X_test/{extension}/{str(j).zfill(5)}.{extension}"
                    pil_image.save(image_filename)  # , quality=95)
                    if j > 10:
                        break

        np.save("./data/mnist/y_train.npy", np.array(y_train))
        np.save("./data/mnist/y_test.npy", np.array(y_test))
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def process_cloud_send_setting(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.setting = json.loads(request.setting)
        self.logger.info("====== get {}======".format(self.setting))

        self.inference_target_path = self.setting['img_path']
        self.target_image_sequence_number = 0 #cloudから設定を受け取るたびにリセットする推論対象のシーケンス番号
        payload = ""  # 正常に受信できた場合は、「共通レスポンスデータ」のpayloadを空文字列を格納する。
        response = CommonResponse(code.SUCCESS, request.request_id, "", payload)
        Tc.execute_tc(
            environment_settings.IOT_NETWORK_DEVICE,
            self.setting['network_delay_time'],
            self.setting['network_dispersion_time'],
            self.setting['network_loss_rate'],
            self.setting['network_band_limitation']
        )
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return response

    def process_do_inference(self):
        # ディレクトリモード
        if os.path.isdir(self.inference_target_path):
            self.logger.debug('DIRECTORY MODE')
            process_target_image_dir = self.inference_target_path
            img_files = sorted(os.listdir(process_target_image_dir))
            for img_file in img_files:
                self.process_target_image_file = os.path.join(process_target_image_dir, img_file)
                save_result.save_inter_or_image(self.setting['current_time_str'], "input/images", self.target_image_sequence_number, self.process_target_image_file)
                process_target_image = Image.open(self.process_target_image_file)
                self.process_target = np.array(process_target_image)

                self.inference_and_send_result()
                self.target_image_sequence_number += 1
        # 通常モード
        else:    
            self.logger.debug('SINGLE MODE')
            self.process_target_image_file = self.inference_target_path

            destination_dir = environment_settings.IOT_VISUALIZE_TARGET_PATH
            if os.path.exists(destination_dir):
                shutil.rmtree(destination_dir)
            os.makedirs(destination_dir)
            # 中間層可視化用に解析対象画像をpngに変換
            self.convert_jpg_to_png(destination_dir)

            save_result.save_inter_or_image(self.setting['current_time_str'], "input/images", self.target_image_sequence_number, self.process_target_image_file)
            process_target_image = Image.open(self.process_target_image_file)
            self.process_target = np.array(process_target_image)
            self.inference_and_send_result()
            self.target_image_sequence_number += 1

        Tc.reset_tc(
            environment_settings.IOT_NETWORK_DEVICE,
            self.setting['network_delay_time'],
            self.setting['network_dispersion_time'],
            self.setting['network_loss_rate'],
            self.setting['network_band_limitation']
        )
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def inference_and_send_result(self):
        if self.setting['layer'] == 0:
            self.split_image_into_packets()
        else:
            # self.set_dummy_result_data()
            self.do_inference()
            self.split_tensor_into_packets()

        # self.send_result_summary()
        # self.send_result_data()
        
        while self.send_result_summary() is False and self.retry_count < environment_settings.MAX_RETRY_COUNT:
            self.retry_count += 1
            self.logger.info(f"retry count is {self.retry_count}")
        if environment_settings.MAX_RETRY_COUNT <= self.retry_count:
            self.logger.error("max retry count is over...")
            return False

        while self.send_result_data() is False and self.retry_count < environment_settings.MAX_RETRY_COUNT:
            self.retry_count += 1
            self.logger.info(f"retry count is {self.retry_count}")
        if environment_settings.MAX_RETRY_COUNT <= self.retry_count:
            self.logger.error("max retry count is over...")
            return False
        return True

    def get_setting_from_cloud_server(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
        req = CommonRequest(command.IOT_GET_SETTING)
        self.logger.debug(f"Request JSON : {req.get_json()}")
        sock.send(req.get_json().encode("ascii"))

        rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
        self.logger.debug(f"Response JSON : {response.get_json()}")
        self.logger.debug(f"Response payload : {response.payload}")

        self.setting = json.loads(response.payload)
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def get_inference_target_from_cloud_server(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
        req = CommonRequest(command.IOT_GET_INFERENCE_TARGET)
        self.logger.debug(f"Request JSON : {req.get_json()}")
        sock.send(req.get_json().encode("ascii"))

        rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
        self.logger.debug(f"Response JSON : {response.get_json()}")
        self.logger.debug(f"Response payload : {response.payload}")

        inference_target_response = json.loads(response.payload)
        self.inference_target_path = inference_target_response['img_path']
        process_target_image_file = self.inference_target_path
        process_target_image = Image.open(process_target_image_file)
        self.process_target = np.array(process_target_image)
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def split_image_into_packets(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        with open(
            self.process_target_image_file,
            "rb",
        ) as f:
            binary_str = f.read()
            empty_str_size = sys.getsizeof(b"")
            each_str_len = self.setting['split_size'] - empty_str_size

            self.p = []
            for i in range(math.ceil(len(binary_str) / each_str_len)):
                self.p.append(
                    base64.b64encode(
                        binary_str[i * each_str_len : (i + 1) * each_str_len]
                    ).decode()
                )

        self.num_elements = len("".join(self.p))
        self.num_packets = len(self.p)
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def split_tensor_into_packets(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        # xは中間層出力を平坦化したもの
        x = self.result_data.flatten()
        n = len(x)
        if self.setting['split_mode'] == 'random':
            # self.kはパケットをランダムに並べ替えるためのインデックス
            # 受信側でも同じシード値を用いるので、元の順番に並べ直すことができる
            np.random.seed(environment_settings.IOT_RANDOM_SEED_SHUFFLE)
            self.k = np.random.permutation(n)
        elif self.setting['split_mode'] == 'sequential':
            self.k = np.arange(n)
        else:
            raise Exception('IOT_SPLIT_MODE has invalid value.')

        s = environment_settings.IOT_SPLITTED_NUMPY_LENGTH

        self.num_elements = 0

        # self.pの各要素が、各パケットのペイロードになる
        self.p = []
        for i in range(0, n, s):
            p_i = []
            for j in range(i, min(i + s, n)):
                p_i.append(x[self.k[j]])
            p_i = np.array(p_i, dtype=np.float16)

            self.num_elements += len(p_i)

            np.save(BUFFER_NPYFILE, p_i)
            with open(BUFFER_NPYFILE, "rb") as f:
                p_i = f.read()
            p_i = base64.b64encode(p_i).decode()
            self.p.append(p_i)

        self.num_packets = len(self.p)

        os.remove(BUFFER_NPYFILE)

        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def send_result_summary(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_PORT))

            filename = os.path.splitext(os.path.basename(self.process_target_image_file))[0]
            request = IotDeviceResultSummaryRequest(
                command.IOT_SEND_RESULT_SUMMARY,
                self.num_packets,
                self.num_elements,
                environment_settings.IOT_RANDOM_SEED_SHUFFLE,
                filename, # 画像のファイル名(拡張子除く)
            )
            self.logger.info(f"IotDeviceResultSummaryRequest : {request.get_json()}")
            sock.send(request.get_json().encode("ascii"))

            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
            self.logger.debug(f"Received data : {rcv_data}")
            response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
            self.logger.debug(f"Response JSON : {response.get_json()}")
            self.logger.debug(f"Response payload : {response.payload}")
            assert response.payload == ""
        except socket.error as se:
            self.logger.exception(se)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def send_result_data(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            self.terminate_sending_result_data_flag = False
            np.random.seed(environment_settings.IOT_RANDOM_SEED_TRANSMISSION_PROBABILITY)
            transmission_start_time = time.time()
            save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Transmission start time = {:.9f}".format(self.target_image_sequence_number, transmission_start_time) + '\n', mode='a')
            
            self.logger.info('use udp = ' + str(self.setting['use_udp']))
            for i in range(len(self.p)):
                if self.terminate_sending_result_data_flag:
                    break
                
                if self.setting['use_udp']:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDPを用いる
                    #sock.bind((environment_settings.IOT_HOSTNAME, environment_settings.IOT_UDP_PORT))
                    # UDPはコネクションレス
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # TCPを用いる
                    sock.connect((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_PORT)) # 接続

                self.logger.debug(f"{i}th packet is sent.")
                payload = self.p[i]
                sequence = i
                request = IotDeviceResultDataRequest(
                    command.IOT_SEND_RESULT_DATA, payload, sequence
                )
                self.logger.debug(f"IotDeviceResultDataRequest : {request.get_json()}")

                if self.setting['use_udp']:
                    # UDPでは接続を確立していないので、宛先を指定して送信する
                    self.logger.debug("send via UDP")
                    sock.sendto(request.get_json().encode("ascii"), (environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_UDP_PORT))

                    '''
                    # UDPの場合はレスポンスを待たない
                    # 以下の行は、UDPで送られてくるレスポンスを受信するためのコード
                    # rcv_data, addr = sock.recvfrom(environment_settings.BUFFER_SIZE)
                    '''

                else:
                    # TCPでは接続を確立している状態で送信する
                    sock.send(request.get_json().encode("ascii"))
                    rcv_data = sock.recv(environment_settings.BUFFER_SIZE)

                    self.logger.debug(f"Received data : {rcv_data}")
                    response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
                    self.logger.debug(f"Response JSON : {response.get_json()}")
                    self.logger.debug(f"Response payload : {response.payload}")
                    assert response.payload == ""
            
            total_send_data_size = sum([len(packet) for packet in self.p])
            save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Send Data Size = {} bytes".format(self.target_image_sequence_number, total_send_data_size) + '\n', mode='a')
            save_result.save_json_or_txt(self.setting['current_time_str'], "output", "condition.txt", "{}, Total Send Packets = {}".format(self.target_image_sequence_number, len(self.p)) + '\n', mode='a')
        except socket.error as se:
            self.logger.exception(se)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False
        except Exception as e:
            self.logger.exception(e)
            self.logger.error(f"===== error {sys._getframe().f_code.co_name} , return False =====")
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def process_send_received_result(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        if request.code == code.SUFFICIENT_DATA_ARRIVAL:
            self.logger.info("SUFFICIENT_DATA_ARRIVAL")
            self.terminate_sending_result_data_flag = True
        elif request.code == code.TIME_EXCEEDED:
            self.logger.info("WAITING_TIME_EXCEEDED")
            self.terminate_sending_result_data_flag = True

        payload = ""  # 正常に受信できた場合は、「共通レスポンスデータ」のpayloadを空文字列を格納する。
        response = CommonResponse(code.SUCCESS, request.request_id, "", payload)

        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return response

    def receive_common_request(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            if os.path.exists('./data/numpy'):
                shutil.rmtree('./data/numpy')
            os.makedirs('./data/numpy', exist_ok=True)
            is_wait = True
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((environment_settings.IOT_HOSTNAME, environment_settings.IOT_PORT))
                s.listen(5)
                while is_wait and self.retry_count < environment_settings.MAX_RETRY_COUNT:
                    self.logger.info('wait receive...')
                    conn, addr = s.accept()
                    data = conn.recv(environment_settings.BUFFER_SIZE)
                    self.logger.debug(f"Request data : {data}")
                    self.logger.debug(f"Request addr : {addr}")
                    converted_req = CommonRequest.convert_from_json(data)
                    self.logger.debug(f"Request JSON : {converted_req.get_json()}")

                    # 終了コマンドは個別で処理する
                    if converted_req.command == command.IOT_END:
                        res = CommonResponse(code.SUCCESS, converted_req.request_id, "", "")
                        conn.sendall(res.get_json().encode())
                        conn.close()
                        is_wait = False
                        break

                    if converted_req.command in self.command_list:
                        if converted_req.command == command.EDGE_SEND_RECEIVED_RESULT:
                            converted_req = (
                                EdgeServerReceivedResultRequest.convert_from_json(data)
                            )
                        elif converted_req.command == command.CLOUD_SEND_SETTING_TO_IOT:
                            converted_req = (
                                CloudServerSettingRequest.convert_from_json(data)
                            )
                        res = self.command_list[converted_req.command](converted_req)
                        conn.sendall(res.get_json().encode())
                    else:
                        self.command_not_found(converted_req)

                    if converted_req.command == command.CLOUD_SEND_SETTING_TO_IOT:
                        thread_process = threading.Thread(target=self.process_do_inference)
                        thread_process.setDaemon(True)
                        thread_process.start()

            Tc.reset_tc(
                environment_settings.IOT_NETWORK_DEVICE,
                self.setting['network_delay_time'],
                self.setting['network_dispersion_time'],
                self.setting['network_loss_rate'],
                self.setting['network_band_limitation']
            )
        except:
            Tc.reset_tc(
                environment_settings.IOT_NETWORK_DEVICE,
                self.setting['network_delay_time'],
                self.setting['network_dispersion_time'],
                self.setting['network_loss_rate'],
                self.setting['network_band_limitation']
            )
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    def send_process_time(self, process_name):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))

        request = ProcessTimeRequest(
            command.IOT_SEND_PROCESS_TIME,
            process_name,
            #(datetime.datetime.now(datetime.timezone(T_DELTA, 'JST'))).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
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

    def command_not_found(self, request):
        raise Exception("command not found")

    def convert_jpg_to_png(self, destination_dir):
        image = Image.open(self.process_target_image_file)
        # jpgファイルの名前を取得（拡張子を除く）
        file_name_without_ext = os.path.splitext(os.path.basename(self.process_target_image_file))[0]
        # pngとして保存するパスを指定
        png_path = os.path.join(destination_dir, file_name_without_ext + '.png')
        image.save(png_path)

if __name__ == "__main__":
    iot_device = IotDevice()
    iot_device.main()
