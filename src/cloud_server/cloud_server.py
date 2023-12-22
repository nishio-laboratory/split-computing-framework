#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import json
import os
import socket
import sys
import threading
import datetime
T_DELTA = datetime.timedelta(hours=9)

from src.conf import environment_settings
from src.lib import code, command, save_result, settings_json
from src.lib.logger import create_logger
from src.lib.model.request import (
    CommonRequest, 
    EdgeServerInferenceResultRequest, 
    CloudServerSettingRequest,
    ProcessTimeRequest
)
from src.lib.model.response import (
    CommonResponse,
)
from src.lib.gui import Gui

# パラメータクラス
class Parameters:
    def __init__(self):
        self.overall = None
        self.edge = None
        self.iot = None
        self.img_path = None

class CloudServer:
    def __init__(self):
        self.command_list = {
            command.IOT_GET_CNN_MODEL: self.process_get_iot_cnn_model,
            command.EDGE_GET_CNN_MODEL: self.process_get_edge_cnn_model,
            command.EDGE_SEND_INFERENCE_RESULT: self.process_send_edge_inference_result,
            command.IOT_SEND_PROCESS_TIME: self.show_process_log_time,
            command.EDGE_SEND_PROCESS_TIME: self.show_process_log_time,
        }
        self.logger = create_logger(__name__)
        self.param = Parameters()
        self.gui = None
        self.inference_results = []
        self.process_time = []

        self.thread_receive = None
        self.thread_send = None
        self.retry_count = 0

    # UIから受け取ったパラメータを展開
    def parameter_expansion(self, overall_param, edge_param, iot_param, img_path):
        
        overall_keys = ('model', 'layer', 'mode', 'split_size', 'PCA_rate', 'Qubit_type', 'reload', 'use_udp')
        edge_keys = ('reach_rate', 'waiting_time', 'edge_network_delay_time', 'edge_network_dispersion_time', 'edge_network_loss_rate', 'edge_network_band_limitation')
        iot_keys = ('network_delay_time', 'network_dispersion_time', 'network_loss_rate', 'network_band_limitation')
        self.param.overall = dict(zip(overall_keys, overall_param))
        self.param.edge = dict(zip(edge_keys, edge_param))
        self.param.iot = dict(zip(iot_keys, iot_param))
        self.param.img_path = img_path

    def send_setting_to_iot_device(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.IOT_HOSTNAME, environment_settings.IOT_PORT))
            to_json_data = {
                "model": self.param.overall['model'],
                "layer": self.param.overall['layer'],
                "split_mode": self.param.overall['mode'],
                "split_size": self.param.overall['split_size'],
                "PCA_rate": self.param.overall['PCA_rate'],
                "Qubit_type": self.param.overall['Qubit_type'],
                "reload": self.param.overall['reload'],
                "use_udp": self.param.overall['use_udp'],
                "network_delay_time": self.param.iot['network_delay_time'],
                "network_dispersion_time": self.param.iot['network_dispersion_time'],
                "network_loss_rate": self.param.iot['network_loss_rate'],
                "network_band_limitation": self.param.iot['network_band_limitation'],
                "img_path": self.param.img_path,
                "current_time_str": self.current_time_str
            }
            setting = json.dumps(to_json_data)
            request = CloudServerSettingRequest(
                command.CLOUD_SEND_SETTING_TO_IOT,
                setting
            )
            self.logger.debug(f"CloudServerSettingRequest : {request.get_json()}")
            sock.send(request.get_json().encode("ascii"))

            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
            self.logger.debug(f"Received data : {rcv_data}")
            response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
            self.logger.debug(f"Response JSON : {response.get_json()}")
            self.logger.debug(f"Response payload : {response.payload}")
            assert response.payload == ""
        except Exception as e:
            self.logger.exception(e)
            self.retry_count += 1
            if self.retry_count < environment_settings.MAX_RETRY_COUNT:
                return self.send_setting_to_iot_device()
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def send_setting_to_edge_server(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_PORT))
            to_json_data = {
                "model": self.param.overall['model'],
                "layer": self.param.overall['layer'],
                "split_mode": self.param.overall['mode'],
                "split_size": self.param.overall['split_size'],
                "PCA_rate": self.param.overall['PCA_rate'],
                "Qubit_type": self.param.overall['Qubit_type'],
                "reload": self.param.overall['reload'],
                "use_udp": self.param.overall['use_udp'],
                "reach_rate": self.param.edge['reach_rate'],
                "waiting_time": self.param.edge['waiting_time'],
                "edge_network_delay_time": self.param.edge['edge_network_delay_time'],
                "edge_network_dispersion_time": self.param.edge['edge_network_dispersion_time'],
                "edge_network_loss_rate": self.param.edge['edge_network_loss_rate'],
                "edge_network_band_limitation": self.param.edge['edge_network_band_limitation'],
                "current_time_str": self.current_time_str
            }
            setting = json.dumps(to_json_data)
            request = CloudServerSettingRequest(
                command.CLOUD_SEND_SETTING_TO_EDGE,
                setting
            )
            self.logger.debug(f"CloudServerSettingRequest : {request.get_json()}")
            sock.send(request.get_json().encode("ascii"))

            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
            self.logger.debug(f"Received data : {rcv_data}")
            response = CommonResponse.convert_from_json(str(rcv_data, "utf-8"))
            self.logger.debug(f"Response JSON : {response.get_json()}")
            self.logger.debug(f"Response payload : {response.payload}")
            assert response.payload == ""
        except Exception as e:
            self.logger.exception(e)
            self.retry_count += 1
            if self.retry_count < environment_settings.MAX_RETRY_COUNT:
                return self.send_setting_to_edge_server()
            return False
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return True

    def process_get_iot_cnn_model(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return self.process_get_cnn_model(request)

    def process_get_edge_cnn_model(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return self.process_get_cnn_model(request)

    def process_get_cnn_model(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return

    def process_send_edge_inference_result(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        file_name = request.filename

        idx = self.param.img_path.find('/images')
        # ディレクトリモードで、画像が正しくimagesというディレクトリに入っていた場合
        if self.dir_mode and idx >= 0: 
            base_path = self.param.img_path[:idx] # imagesとlabelsが入っているべきディレクトリのパス
            label_dir = os.path.join(self.iot_device_path, base_path, 'labels') # ラベルのテキストファイルが入っているディレクトリのパス
            label_path = os.path.join(label_dir, file_name + '.txt') # ラベルのパス
            # ラベルが存在する場合、以下の処理を実行
            if os.path.isfile(label_path):
                self.logger.info(f'label exists at {os.path.relpath(label_path, self.iot_device_path)}')

                with open(label_path, 'r') as f:
                    label = f.read().strip()
                
                # 辞書形式で、画像ファイル名をkey、{推論結果, ラベル}をvalueとして保持しておく
                message = 'Inference result is correct!!' if request.result == label else 'Inference result is incorrect...'
                self.result_summary[file_name] = {'inference result': request.result, 'label': label, 'message': message}
                self.logger.info(self.result_summary[file_name])
                self.inference_results.append({ 'result': request.result, 'label': label })
                self.gui.put_value_output("Inference result = {}, Label = {}, {}, accuracy rate = {}\n".format(request.result, label, message, self.get_accuracy_rate()))
            else:
                self.logger.info('no label exists')
                self.gui.put_value_output('no label exists')
        elif not self.dir_mode:
            self.gui.put_value_output('Inference result: ' + request.result)

        save_result.save_json_or_txt(self.current_time_str, "output", "result.txt", request.result + '\n', mode='a')

        payload = ""
        res = CommonResponse(code.SUCCESS, request.request_id, "", payload)
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        return res

    def command_not_found(self, request):
        # raise Exception("command not found")
        self.logger.error('command not found' + str(request))

    def wait_receive(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        is_wait = True
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
            s.listen(5)
            while is_wait:
                conn, addr = s.accept()
                data = conn.recv(environment_settings.BUFFER_SIZE)
                self.logger.debug(f"data-> {data}, addr-> {addr}")
                converted_req = CommonRequest.convert_from_json(data)
                self.logger.debug(converted_req.get_json())

                # 終了コマンドは個別で処理する
                if converted_req.command == command.CLOUD_END:
                    res = CommonResponse(code.SUCCESS, converted_req.request_id, "", "")
                    conn.sendall(res.get_json().encode())
                    conn.close()
                    if self.thread_send is not None:
                        self.thread_send.join()
                    is_wait = False
                    s.close()
                    break

                if converted_req.command in self.command_list:
                    if converted_req.command == command.EDGE_SEND_INFERENCE_RESULT:
                        converted_req = (
                            EdgeServerInferenceResultRequest.convert_from_json(data)
                        )
                    elif converted_req.command == command.IOT_SEND_PROCESS_TIME:
                        converted_req = (
                            ProcessTimeRequest.convert_from_json(data)
                        )
                    elif converted_req.command == command.EDGE_SEND_PROCESS_TIME:
                        converted_req = (
                            ProcessTimeRequest.convert_from_json(data)
                        )

                    res = self.command_list[converted_req.command](converted_req)
                    conn.sendall(res.get_json().encode())
                else:
                    self.command_not_found(converted_req)
                conn.close()

                is_wait = not self.gui.is_disable_ui()
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    # パラメータ設定用UIを表示し、エッジサーバ、IoTデバイスに送信
    def send_setting(self):
        while True:
            self.gui = Gui()
            ui_result = self.gui.show_setting() # UI表示

            if ui_result == Gui.RETURN_CLOSE_SETTING:
                if self.thread_receive is not None:
                    self.send_end_command()
                    self.thread_receive.join()
                self.gui = None
                return
            elif ui_result == Gui.RETURN_CLOSE_CONFIRM:
                self.gui = None
                continue

            overall_param, iot_param, edge_param, img_path = self.gui.get_params()
            self.parameter_expansion(overall_param, edge_param, iot_param, img_path)


            self.current_time_str = datetime.datetime.now(
                datetime.timezone(datetime.timedelta(hours=9))
            ).strftime("%y%m%d_%H%M%S") #シミュレーション結果ファイルを保存するフォルダ名のための現在時刻

            with open('../conf/settings.json', 'r') as file:
                existing_data = json.load(file)
            merged_data = {**existing_data, **self.param.__dict__}
            save_result.save_json_or_txt(self.current_time_str, "input", "settings.json", merged_data, is_json=True)


            self.iot_device_path = '../iot_device' # cloud_serverディレクトリから見たiot_deviceのパス
            img_abs_path = os.path.join(self.iot_device_path, self.param.img_path)
            # ディレクトリモード
            if os.path.isdir(img_abs_path):
                self.logger.info('DIRECTORY MODE')
                self.dir_mode = True
                self.result_summary = {}
            # 通常モード
            else:
                self.logger.info('SINGLE MODE')
                self.dir_mode = False

            self.inference_results = []
            thread_send_setting_edge = threading.Thread(target=self.send_setting_to_edge_server)
            thread_send_setting_iot = threading.Thread(target=self.send_setting_to_iot_device)
            thread_send_setting_edge.start()
            thread_send_setting_iot.start()
            self.logger.info("===== start gui.show_output_window =====")
            self.gui.show_output_window()
            self.logger.info("===== end gui.show_output_window =====")
            if environment_settings.MAX_RETRY_COUNT <= self.retry_count:
                break;

    def send_setting_without_ui(self):
        self.gui = Gui()
        overall_param = (
            self.settings.overall['model'],
            self.settings.overall['layer'],
            self.settings.overall['mode'],
            self.settings.overall['split_size'],
            self.settings.overall['PCA_rate'],
            self.settings.overall['Qubit_type'],
            self.settings.overall['reload'],
            self.settings.overall['use_udp']
        )
        iot_param = (
            self.settings.iot['network_delay_time'],
            self.settings.iot['network_dispersion_time'],
            self.settings.iot['network_loss_rate'],
            self.settings.iot['network_band_limitation']
        )
        edge_param = (
            self.settings.edge['reach_rate'],
            self.settings.edge['waiting_time'],
            self.settings.edge['edge_network_delay_time'],
            self.settings.edge['edge_network_dispersion_time'],
            self.settings.edge['edge_network_loss_rate'],
            self.settings.edge['edge_network_band_limitation']
        )
        img_path = self.settings.img_path
        self.parameter_expansion(overall_param, edge_param, iot_param, img_path)

        self.current_time_str = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        ).strftime("%y%m%d_%H%M%S") #シミュレーション結果ファイルを保存するフォルダ名のための現在時刻

        save_result.save_json_or_txt(self.current_time_str, "input", "settings.json", self.settings.__dict__, is_json=True)

        self.iot_device_path = '../iot_device' # cloud_serverディレクトリから見たiot_deviceのパス
        img_abs_path = os.path.join(self.iot_device_path, self.param.img_path)
        # ディレクトリモード
        if os.path.isdir(img_abs_path):
            self.logger.info('DIRECTORY MODE')
            self.dir_mode = True
            self.result_summary = {}
        # 通常モード
        else:
            self.logger.info('SINGLE MODE')
            self.dir_mode = False

        self.inference_results = []
        thread_send_setting_edge = threading.Thread(target=self.send_setting_to_edge_server)
        thread_send_setting_iot = threading.Thread(target=self.send_setting_to_iot_device)
        thread_send_setting_edge.start()
        thread_send_setting_iot.start()
        self.logger.info("===== start gui.show_output_window =====")
        self.gui.show_output_window()
        self.logger.info("===== end gui.show_output_window =====")

    def show_process_log_time(self, request):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        if "start" in request.process_name:    # 処理の開始時
            self.logger.info("process_name = {}".format(request.process_name))
            self.gui.put_value_output("process_name = {}".format(request.process_name))
        else:   #処理の終了時
            self.logger.info("process_name = {}, process_time = {:.9f}".format(request.process_name, request.process_time - self.process_time[-1]))
            self.gui.put_value_output("process_name = {}, process_time = {:.9f}".format(request.process_name, request.process_time - self.process_time[-1]))
        payload = ""
        res = CommonResponse(code.SUCCESS, request.request_id, "", payload)
        self.logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
        self.process_time.append(request.process_time)
        return res
    
    def send_end_command(self):
        self.logger.info(f"===== start {sys._getframe().f_code.co_name} =====")

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.IOT_HOSTNAME, environment_settings.IOT_PORT))
            request = CommonRequest(command.IOT_END)
            sock.send(request.get_json().encode("ascii"))
            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        except Exception as e:
            self.logger.exception(e)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.EDGE_HOSTNAME, environment_settings.EDGE_PORT))
            request = CommonRequest(command.EDGE_END)
            sock.send(request.get_json().encode("ascii"))
            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        except Exception as e:
            self.logger.exception(e)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((environment_settings.CLOUD_HOSTNAME, environment_settings.CLOUD_PORT))
            request = CommonRequest(command.CLOUD_END)
            sock.send(request.get_json().encode("ascii"))
            rcv_data = sock.recv(environment_settings.BUFFER_SIZE)
        except Exception as e:
            self.logger.exception(e)

        self.logger.info(f"===== end {sys._getframe().f_code.co_name} =====")

    def get_accuracy_rate(self):
        total_count = 0
        correct_count = 0
        for result in self.inference_results:
            total_count += 1
            if result['result'] == result['label']:
                correct_count += 1
        if total_count != 0:
            return correct_count / total_count
        return 0

    def main(self):
        if len(sys.argv) >= 2:
            settings_file_path = sys.argv[1]
            self.settings = settings_json.Settings(settings_file_path)
        # マルチスレッドで、受信の口を開きながらUIを立ち上げる
        self.thread_receive = threading.Thread(target=self.wait_receive)
        self.thread_receive.setDaemon(True)
        self.thread_receive.start()
        if len(sys.argv) >= 2:
            self.send_setting_without_ui()
        else:
            # 引数で何も指定しなかったらUI立ち上げてsettingを行う
            self.send_setting()


if __name__ == "__main__":
    cloud_server = CloudServer()
    cloud_server.main()
