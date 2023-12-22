import PySimpleGUI as sg
import os
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from pathlib import Path
import random
import re
from src.lib import compressor, settings_json

import time

class Gui:
    RETURN_CLOSE_SETTING = 0
    RETURN_CLOSE_CONFIRM = 1
    RETURN_CLOSE_OUTPUT = 2
    def __init__(self):
        self.settings = settings_json.Settings('../conf/settings.json')
        self.disable_ui = False
        sg.theme('Gray Gray Gray')

        # 画像フォルダのパスに関する設定
        self.iot_device_path = '../iot_device' # cloud_serverディレクトリから見たiot_deviceのパス
        self.data_dir = os.path.join(self.iot_device_path, 'data') # 画像+ラベルのデータが含まれるディレクトリ
        #self.default_dir = os.path.join(self.data_dir, self.settings.DEFAULT_DIRECTORY) # img_dir_browseのinitial_folderとする。
        self.default_dir = os.path.join(self.iot_device_path, os.path.dirname(self.settings.img_path)) # img_dir_browseのinitial_folderとする。
        self.img_dir = '' # 選択した推論対象の画像ファイルを含むディレクトリを格納する変数
        img_files = [''] # 選択したディレクトリに含まれるファイル名を格納するリスト
        self.img_file = '' # 画像ファイル名

        # ウィンドウの部品のパラメータを定義
        self.img_area_width, self.img_area_height = (180, 180) # 画像表示領域のサイズを指定

        # ウィンドウの部品を定義
        # 画像ファイル名選択コンボボックスおよび画像表示領域の部品群
        img_settings_text = sg.Text('Image settings', size=(30, 1), font=('bold'))
        img_dir_prompt = sg.Text("Image directory:")
        img_dir_name = sg.Input(enable_events=True, size=(30,1), readonly=True, key='img_dir_name')
        img_dir_browse = sg.FolderBrowse(initial_folder=self.default_dir, key="img_dir_browse", target='img_dir_name')
        img_file_prompt = sg.Text("Test image to be inferred:")
        img_combo = sg.Combo(values = img_files, size=(20,1), enable_events=True, readonly=True, key='img_combo')
        img_random_button = sg.Button('random', key='img_random_button')
        img_status = sg.Text('No image selected:', key='img_status')
        img_area = sg.Image(size=(self.img_area_width, self.img_area_height), background_color='black', key="img_area")

        # ウィンドウの部品を機能ごとにまとめる
        # 画像ファイル名選択コンボボックスおよび画像表示領域
        img_select_and_display = [
            [img_settings_text],
            [img_dir_prompt],
            [img_dir_name, img_dir_browse],
            [img_file_prompt],
            [img_combo, img_random_button],
            [img_status],
            [img_area],
        ]
        # 全体の設定部分
        overall_setting_1 = [
            [sg.Text('Overall settings', size=(30, 1), font=('bold'))],
            [sg.Text('Inference model:', size=(30, 1))],
            [sg.Combo(['model_COMtune', 'my_model'], default_value=os.path.basename(self.settings.overall['model']), readonly=True, size=(30, 1), key='model')],
            [sg.Text('Splitting layer:', size=(30, 1))],
            [sg.InputText(key='layer', size=(30, 1), default_text=self.settings.overall['layer'])],
            [sg.Text('Splitting mode:', size=(30, 1))],
            [sg.Combo(['random', 'sequential'], default_value=self.settings.overall['mode'], readonly=True, size=(30, 1), key='mode')],
            [sg.Text('Splitting size:', size=(30, 1))],
            [sg.InputText(key='size', size=(30, 1), default_text=self.settings.overall['split_size'])],
            [sg.Text('PCA compression rate:', size=(30, 1))],
            [sg.InputText(key='PCArate', size=(30, 1), default_text=self.settings.overall['PCA_rate'])],
            [sg.Text('Qubit compression type:', size=(30, 1))],
            [sg.Combo(compressor.Compressor.qubit_pattern(), readonly=True, default_value=self.settings.overall['Qubit_type'], size=(30, 5), key='Qubittype')],
            [sg.Text('Load Model:', size=(30, 1))],
            [sg.Checkbox('Every Time', size=(30, 1), key='reload', default=self.settings.overall['reload'])],
            [sg.Text('', size=(30,1))],
            #[sg.Text('', size=(30,1))],
            [sg.Text('Data Transmission Protocol', size=(30,1))],
            [sg.Radio("TCP", "protocol", key="use_tcp", default=True)],
            [sg.Radio("UDP", "protocol", key="use_udp")],
        ]
        # IoTデバイスの設定部分
        iot_device_setting_1 = [
            [sg.Text('IoT device settings', size=(30, 1), font=('bold'))],
            [sg.Text('Network latency:', size=(30, 1))],
            [sg.InputText(key='latency', size=(30, 1), default_text=self.settings.iot['network_delay_time'])],
            [sg.Text('Variation in network latency:', size=(30, 1))],
            [sg.InputText(key='variation', size=(30, 1), default_text=self.settings.iot['network_dispersion_time'])],
            [sg.Text('Network loss ratio:', size=(30, 1))],
            [sg.InputText(key='loss', size=(30, 1), default_text=self.settings.iot['network_loss_rate'])],
            [sg.Text('Network Band Limitation', size=(30,1))],
            [sg.InputText(key='band_limitation', size=(30, 1), default_text=self.settings.iot['network_band_limitation'])],
        ]
        # エッジサーバーの設定部分
        edge_server_setting_1 = [
            [sg.Text('Edge server settings', size=(30, 1), font=('bold'))],
            [sg.Text('Data arrival rate:', size=(30, 1))],
            [sg.InputText(key='arrival_rate', size=(30, 1), default_text=self.settings.edge['reach_rate'])],
            [sg.Text('Data waiting time:', size=(30, 1))],
            [sg.InputText(key='wait_time', size=(30, 1), default_text=self.settings.edge['waiting_time'])],
            [sg.Text('Network latency:', size=(30, 1))],
            [sg.InputText(key='edge_latency', size=(30, 1), default_text=self.settings.edge['edge_network_delay_time'])],
            [sg.Text('Variation in network latency:', size=(30, 1))],
            [sg.InputText(key='edge_variation', size=(30, 1), default_text=self.settings.edge['edge_network_dispersion_time'])],
            [sg.Text('Network loss ratio:', size=(30, 1))],
            [sg.InputText(key='edge_loss', size=(30, 1), default_text=self.settings.edge['edge_network_loss_rate'])],
            [sg.Text('Network Band Limitation', size=(30,1))],
            [sg.InputText(key='edge_band_limitation', size=(30, 1), default_text=self.settings.edge['edge_network_band_limitation'])],
        ]
        # 確定ボタン
        confirm_button = [sg.Button('Confirm', key = 'read')]
        setting_close_button = [sg.Button('Close', key = 'setting_close')]

        # レイアウトを作成
        layout1 = [[
            sg.Column(overall_setting_1, vertical_alignment='top'), 
            sg.Column([*iot_device_setting_1, *edge_server_setting_1], vertical_alignment='top'), 
            sg.Column([*img_select_and_display], vertical_alignment='top')
        ], [
            sg.Column([setting_close_button], vertical_alignment='top', justification='l'),
            sg.Column([confirm_button], vertical_alignment='top', justification='r')
        ]]

        self.default_values = {
            'model': 'Choose model', 'layer': '', 'mode': 'Choose mode', 'reload':'',
            'size': '', 'PCArate': '', 'Qubittype': 'Choose type', 
            'latency': '', 'variation': '', 'loss': '', 'band_limitation': '', 'arrival_rate': '', 'wait_time': '',
            'edge_latency': '', 'edge_variation': '', 'edge_loss': '', 'edge_band_limitation': ''
        }

        # 必須入力にしたい項目のkeyをcheck_keysに入れておく
        self.check_keys = [
            'model', 'layer', 'mode', 'size', 'PCArate', 'Qubittype',
            'latency', 'variation', 'loss', 'band_limitation', 'arrival_rate', 'wait_time',
            'edge_latency', 'edge_variation', 'edge_loss', 'edge_band_limitation'
        ]

        self.window1 = sg.Window('Settings for Distributed Machine Learning', layout1, finalize=True)

        # overall_param, iot_param, edge_paramに全体の設定, IoTデバイスの設定, エッジサーバの設定をそれぞれタプルで格納
        self.overall_param, self.iot_param, self.edge_param, self.layout2 = None, None, None, None

        # 確認画面のレイアウト作成
        overall_setting_2 = [
            [sg.Text('Overall settings', size=(30, 1), font=('bold'))],
            [sg.Text(f"Inference model:\t{self.default_values['model']}", size=(30, 1), key='model')],
            [sg.Text(f"Splitting layer:\t{self.default_values['layer']}", size=(30, 1), key='layer')],
            [sg.Text(f"Splitting mode:\t{self.default_values['mode']}", size=(30, 1), key='mode')],
            [sg.Text(f"Splitting size:\t{self.default_values['size']}", size=(30, 1), key='size')],
            [sg.Text(f"PCA compression rate:\t{self.default_values['PCArate']}", size=(30, 1), key='PCArate')],
            [sg.Text(f"Qubit compression type:\t{self.default_values['Qubittype']}", size=(40, 1), key='Qubittype')],
            [sg.Text(f"Load Model Every Time:\t{self.default_values['reload']}", size=(40, 1), key='reload')],
            [sg.Text(f"Data transmission protocol:\t", size=(30, 1), key='protocol')],
        ]
        iot_device_setting_2 = [
            [sg.Text('IoT device settings', size=(30, 1), font=('bold'))],
            [sg.Text(f"Network latency:\t{self.default_values['latency']}", size=(30, 1), key='latency')],
            [sg.Text(f"Variation in network latency:\t{self.default_values['variation']}", size=(30, 1), key='variation')],
            [sg.Text(f"Network loss ratio:\t{self.default_values['loss']}", size=(30, 1), key='loss')],
            [sg.Text(f"Network band limitation:\t{self.default_values['band_limitation']}", size=(30, 1), key='band_limitation')],
        ]
        edge_server_setting_2 = [
            [sg.Text('Edge server settings', size=(30, 1), font=('bold'))],
            [sg.Text(f"Data arrival rate:\t{self.default_values['arrival_rate']}", size=(30, 1), key='arrival_rate')],
            [sg.Text(f"Data waiting time:\t{self.default_values['wait_time']}", size=(30, 1), key='wait_time')],
            [sg.Text(f"Edge network latency:\t{self.default_values['edge_latency']}", size=(30, 1), key='edge_latency')],
            [sg.Text(f"Edge variation in network latency:\t{self.default_values['edge_variation']}", size=(30, 1), key='edge_variation')],
            [sg.Text(f"Edge network loss ratio:\t{self.default_values['edge_loss']}", size=(30, 1), key='edge_loss')],
            [sg.Text(f"Edge network band limitation:\t{self.default_values['edge_loss']}", size=(30, 1), key='edge_band_limitation')],
        ]
        img_name = [
            [sg.Text('Image name', size=(30, 1), font=('bold'))],
            [sg.Text('', key='img_path')],
            [sg.Image(size=(self.img_area_width, self.img_area_height), key='img_confirm_area')]
        ]
        exec_button = [sg.Button('Execute', key = 'ok')]
        back_button = [sg.Button('Back', key = 'back')]
        self.layout2 = [[
            sg.Column(overall_setting_2, vertical_alignment='top'),
            sg.Column([*iot_device_setting_2, *edge_server_setting_2], vertical_alignment='top'),
            sg.Column([*img_name], vertical_alignment='top')
        ], [
            sg.Column([back_button], vertical_alignment='top', justification='l'),
            sg.Column([exec_button], vertical_alignment='top', justification='r')
        ]]

        self.window2 = sg.Window('Set Params', self.layout2, finalize=True)

        self.window3 = None
        self.layout_output = None
        self.output_text_area = None
        self.output_text = ""

    # デフォルトの値のままか不適切な範囲のパラメータが存在したらTrueを返す関数    
    def check_params(self, keys, default_params, params):
        nonnegative_integer = ['layer', 'size', 'wait_time']
        p1 = '[0-9]+'   # 非負整数の正規表現
        nonnegative_number = ['latency', 'variation', 'band_limitation', 'edge_latency', 'edge_variation', 'edge_band_limitation', 'edge_band_limitation']
        p2 = '[0-9]+(\.[0-9]+)?'   # 非負の数（整数または小数）の正規表現
        float_0to1 = ['PCArate', 'loss', 'arrival_rate', 'edge_loss']
        p3 = '1(\.0+)?|0(\.[0-9]+)?'    # 0から1までの小数の正規表現
        for key in keys:
            if default_params[key] == params[key]:
                return True, "The '" + key + "' field is not filled in."
            if key in nonnegative_integer:
                if not re.fullmatch(p1, params[key]):
                    return True, "The value of '" + key + "' must be nonnegative integer. "
            elif key in nonnegative_number:
                if not re.fullmatch(p2, params[key]):
                    return True, "The value of '" + key + "' must be nonnegative number. "
            elif key in float_0to1:
                if not re.fullmatch(p3, params[key]):
                    return True, "The value of '" + key+ "' must be between 0 and 1."

        return False, ""

    # sg.Imageのdataに渡すために、Imageオブジェクトをbytesオブジェクトに変換する関数
    def img_obj_to_data(self, img_obj):
        with BytesIO() as output:
            img_obj.save(output, format="PNG")
            img_data = output.getvalue()
        return img_data

    # 画像パスをチェックし，ファイルが存在しない場合とファイルが認識されない場合はNoneを返す
    # 画像パスが正しくファイルを挿していた場合は，img_objを返す
    def check_img(self, img_dir, img_file):

        if img_file == 'ALL':
            self.window1['img_status'].update(f"Directory Mode (Directory Name : {os.path.relpath(os.path.join(img_dir, '..'), self.data_dir)})")
            self.window1['img_area'].update(data=None)
            return 'ALL'

        # 選択された画像のパス
        img_path = os.path.join(img_dir, img_file)

        # 画像ファイルが存在しない場合、エラー
        if not Path(img_path).is_file():
            self.window1['img_status'].update('Error: Image file not found !')
            # TODO:img_areaを黒い四角に戻す
            # 以下のようにすると、img_areaごと見えなくなってしまう
            self.window1['img_area'].update(data=None)
            return None
        
        # 画像ファイルを読み込む
        try:
            img_obj = Image.open(img_path)
        # 画像ファイルが認識されない場合、エラー
        except UnidentifiedImageError:
            self.window1['img_status'].update("Error: Cannot identify image file !")
            # TODO:img_areaを黒い四角に戻す
            # 以下のようにすると、img_areaごと見えなくなってしまう
            self.window1['img_area'].update(data=None)
            return None
        
        return img_obj

    # 画像表示領域を更新する関数
    # img_dir:画像ファイルを含むディレクトリ名、img_file:画像ファイル名
    # エラーが起きた場合-1を返す
    def update_img_area(self, img_dir, img_file):
        
        img_obj = self.check_img(img_dir, img_file)
        if img_obj == None or img_obj == 'ALL':
            return -1

        # 選択された画像のファイル名をimg_statusに表示
        # iot_deviceのdataから見たimg_dirの相対パスと併せて表示
        self.window1['img_status'].update(os.path.join(os.path.relpath(img_dir, self.data_dir), img_file))

        # 画像表示領域に合わせて画像をリサイズ (画像表示領域の縦横狭い方に合わせる)
        img_w, img_h = img_obj.size # MNISTの場合、(28, 28)
        img_scale = min(self.img_area_width / img_w, self.img_area_height / img_h) 
        img_obj = img_obj.resize((int(img_w * img_scale), int(img_h * img_scale)))
        # Imageオブジェクトをbytesオブジェクトに変換
        img_data = self.img_obj_to_data(img_obj)

        # 画像表示領域を更新し、画像を表示
        self.window1['img_area'].update(data=img_data, size=(self.img_area_width, self.img_area_height))

    def update_img_confirm_area(self, img_dir, img_file):

        img_obj = self.check_img(img_dir, img_file)
        if img_obj == None or img_obj == 'ALL':
            return -1

        # 画像表示領域に合わせて画像をリサイズ (画像表示領域の縦横狭い方に合わせる)
        img_w, img_h = img_obj.size # MNISTの場合、(28, 28)
        img_scale = min(self.img_area_width / img_w, self.img_area_height / img_h) 
        img_obj = img_obj.resize((int(img_w * img_scale), int(img_h * img_scale)))
        # Imageオブジェクトをbytesオブジェクトに変換
        img_data = self.img_obj_to_data(img_obj)

        # 画像表示領域を更新し、画像を表示
        self.window2['img_confirm_area'].update(data=img_data, size=(self.img_area_width, self.img_area_height))

    # self.img_dir内の画像に対応するラベルがself.label_dir内に存在しない場合、ラベルの存在しない画像の名前を返す
    def check_label_dir(self):
        if os.path.isdir(self.label_dir):
            img_files = [x for x in self.img_files if x != 'ALL']
            label_files = sorted([f for f in os.listdir(self.label_dir) if f.endswith('.txt')])

            for i in range(len(img_files)):
                
                if img_files[i].split('.')[0] != label_files[i].split('.')[0]:
                    return img_files[i]

        return None

    def update_img_combo(self):
        # 選択されたディレクトリ下のファイル名のリスト(ディレクトリは除く)
        if os.path.isdir(self.img_dir):
            self.img_files = sorted([f for f in os.listdir(self.img_dir) if os.path.isfile(os.path.join(self.img_dir, f))])
            # リストが空になった場合、エラー回避のため空文字を追加しておく
            if self.img_files == [] : self.img_files.append('')

            # 選択したディレクトリと同階層に'labels'ディレクトリが存在する場合、'ALL'の選択肢を追加する。
            self.label_dir = os.path.join(self.img_dir, '../labels')
            if os.path.isdir(self.label_dir):
                self.img_files = ['ALL'] + self.img_files

            # img_comboのvaluesを更新
            self.window1['img_combo'].update(values=self.img_files)
            # コンボボックスの値を、選択されたディレクトリ内の0番目のファイルとする
            self.img_file = self.img_files[0]
            self.window1.find_element('img_combo').update(value=self.img_file) 
            # 画像表示領域を更新(エラーが出たらcontinue)
            if self.update_img_area(self.img_dir, self.img_file) == -1: 
                return -1

    # デフォルトの値のままのパラメータをチェックし，なければ確認画面を表示
    def show_setting(self):
        flg = True
        self.window1['img_dir_name'].update(value=os.path.abspath(self.default_dir))
        self.img_dir = self.default_dir
        self.update_img_combo()
        while flg:
            self.window1.un_hide()
            self.window2.hide()
            while True:
                event, self.values = self.window1.read()

                if event == sg.WIN_CLOSED or event == 'setting_close':
                    flg = False
                    if self.window3 is not None:
                        self.window3.close()
                    return self.RETURN_CLOSE_SETTING
                
                if event == 'read':
                    #入力していない項目がある場合にポップアップを表示してループ続行
                    check, text = self.check_params(self.check_keys, self.default_values, self.values)
                    if check:
                        sg.popup(text, title='Error')
                        continue
                    # 画像パスが画像を指していない場合，ポップアップを表示してループ続行
                    if self.check_img(self.img_dir, self.img_file) == None:
                        sg.popup('Image not selected correctly.', title='Error')
                        continue
                    # ディレクトリモードを選んでいるのにラベルが1対1対応していない場合、ポップアップを表示してループ続行
                    check_label_dir = self.check_label_dir()
                    if self.img_file == 'ALL' and check_label_dir != None:
                        sg.popup(f'The .txt file corresponding to {check_label_dir} does not exist.', title='Error')
                        continue

                    self.overall_param = (
                        self.values['model'],
                        self.values['layer'],
                        self.values['mode'],
                        self.values['size'],
                        self.values['PCArate'],
                        self.values['Qubittype'],
                        self.values['reload'],
                        self.values['use_udp']
                    )
                    self.iot_param = (
                        self.values['latency'],
                        self.values['variation'],
                        self.values['loss'],
                        self.values['band_limitation']
                    )
                    self.edge_param = (
                        self.values['arrival_rate'],
                        self.values['wait_time'],
                        self.values['edge_latency'],
                        self.values['edge_variation'],
                        self.values['edge_loss'],
                        self.values['edge_band_limitation']
                    )

                    #layout2: 確認画面のレイアウトのパラメータ部分の更新
                    self.window2['model'].update(f"Inference model:\t{self.values['model']}")
                    self.window2['layer'].update(f"Splitting layer:\t{self.values['layer']}")
                    self.window2['mode'].update(f"Splitting mode:\t{self.values['mode']}")
                    self.window2['size'].update(f"Splitting size:\t{self.values['size']}")
                    self.window2['PCArate'].update(f"PCA compression rate:\t{self.values['PCArate']}")
                    self.window2['Qubittype'].update(f"Qubit compression type:\t{self.values['Qubittype']}")
                    self.window2['reload'].update(f"do_reload_model:\t{self.values['reload']}")
                    self.window2['protocol'].update(f"Data transmission protocol:\t{'UDP' if self.values['use_udp'] else 'TCP'}")
                    self.window2['latency'].update(f"Network latency:\t{self.values['latency']}")
                    self.window2['variation'].update(f"Variation in network latency:\t{self.values['variation']}")
                    self.window2['loss'].update(f"Network loss ratio:\t{self.values['loss']}")
                    self.window2['band_limitation'].update(f"Network band limitation:\t{self.values['band_limitation']}")
                    self.window2['arrival_rate'].update(f"Data arrival rate:\t{self.values['arrival_rate']}")
                    self.window2['wait_time'].update(f"Data waiting time:\t{self.values['wait_time']}")
                    self.window2['edge_latency'].update(f"Edge_network latency:\t{self.values['edge_latency']}")
                    self.window2['edge_variation'].update(f"Edge_variation in network latency:\t{self.values['edge_variation']}")
                    self.window2['edge_loss'].update(f"Edge_network loss ratio:\t{self.values['edge_loss']}")
                    self.window2['edge_band_limitation'].update(f"Edge_network band limitation:\t{self.values['edge_band_limitation']}")
                    break

                # img_dir_nameが変化した際にイベントが発生
                # img_dir_browseのイベントとしたかったが、img_dir_browseのenable_events=Trueとしてもなぜかうまくいかなかった
                # 選択したディレクトリの0番目のファイルがコンボボックスで選択された状態にし、img_comboイベントを発生させる
                if event == 'img_dir_name':
                    # img_dirを選択されたディレクトリとする
                    self.img_dir = self.values['img_dir_name']
                    if self.update_img_combo() == -1: 
                        continue
                    self.values['img_combo'] = self.img_file

                # img_random_buttonを押した際に、画像をディレクトリからランダムに選択
                # コンボボックスの値を選択された画像で更新し、img_comboイベントを発生させる
                if event == 'img_random_button':
                    # img_dirを選択されたディレクトリとする
                    self.img_dir = self.values['img_dir_name']
                    # コンボボックスの値を、ランダムに選択されたファイルの名前とする
                    self.img_file = random.choice([x for x in self.img_files if x != 'ALL'])
                    # コンボボックスの表示値を更新
                    self.window1.find_element('img_combo').update(value=self.img_file) 
                    self.values['img_combo'] = self.img_file
                    # 画像表示領域を更新(エラーが出たらcontinue)
                    if self.update_img_area(self.img_dir, self.img_file) == -1: continue

                # 画像ファイル名選択コンボボックスでファイル名が選択された場合にイベントが発生し、選択された画像を表示
                if event == 'img_combo':
                    # img_dirを選択されたディレクトリとする
                    self.img_dir = self.values['img_dir_name']
                    # img_fileをコンボボックスの値にする
                    self.img_file = self.values['img_combo']
                    # 画像表示領域を更新(エラーが出たらcontinue)
                    if self.update_img_area(self.img_dir, self.img_file) == -1: continue

            # 確認画面表示
            if (self.overall_param, self.iot_param, self.edge_param) != (None, None, None):
                self.window2['img_path'].update(os.path.join(os.path.relpath(self.img_dir, self.data_dir), self.img_file))
                self.update_img_confirm_area(self.img_dir, self.img_file)
                self.window1.hide()
                self.window2.un_hide()

                while True:
                    event, self.values = self.window2.read()

                    if event == sg.WIN_CLOSED:
                        flg = False
                        if self.window3 is not None:
                            self.window3.close()
                        return self.RETURN_CLOSE_CONFIRM

                    if event == 'ok':
                        flg = False
                        break

                    if event == 'back':
                        break
        self.window1.close()
        self.window2.close()

    def get_params(self):

        model, layer, mode, size, PCArate, Qubittype, reload, use_udp = self.overall_param
        latency, variation, loss, band_limitation = self.iot_param
        arrival_rate, wait_time, edge_latency, edge_variation, edge_loss, edge_band_limitation = self.edge_param

        # 適切な型に変換する
        model = os.path.join('../lib/saved_model/', model)
        layer = int(layer)
        mode = mode
        size = int(size) # floatではない
        PCArate = float(PCArate)
        latency = float(latency)
        variation = float(variation)
        loss = float(loss)
        band_limitation = float(band_limitation)
        arrival_rate = float(arrival_rate)
        wait_time = int(wait_time)
        edge_latency = float(edge_latency)
        edge_variation = float(edge_variation)
        edge_loss = float(edge_loss)
        edge_band_limitation = float(edge_band_limitation)

        # 'ALL'が選択された場合は、ディレクトリのパスを返す
        if self.img_file == 'ALL':
            img_path = os.path.relpath(self.img_dir, self.iot_device_path)
        else:
            # 画像の，IoTデバイスから見た相対パス
            img_path = os.path.relpath(os.path.join(self.img_dir, self.img_file), self.iot_device_path)

        # TODO: GUI上の変数名と、コード上の変数名が異なる
        # →GUIの方を他に揃える

        return (model, layer, mode, size, PCArate, Qubittype, reload, use_udp), \
                (latency, variation, loss, band_limitation), \
                (arrival_rate, wait_time, edge_latency, edge_variation, edge_loss, edge_band_limitation), \
                img_path

    def show_output_window(self):
        self.output_text_area = sg.Text(self.output_text, size=(100, 50), background_color='black', text_color='white')
        self.layout_output = [
            [sg.Text('Output', size=(30, 1), font=('bold'))],
            [sg.Column([[self.output_text_area]], scrollable=True)],
            [sg.Button('Close', key = 'close')]
        ]
        self.window3 = sg.Window('Output', self.layout_output, finalize=True)

        while True:
            event, values = self.window3.read()
            if event == sg.WIN_CLOSED:
                break
            if event == 'close':
                break

        self.window3.close()
        self.disable_ui = True
        self.output_text_area = None
        self.layout = None
        self.window3 = None
        self.output_text = ""

    def put_value_output(self, val):
        # sleepを入れないとオブジェクト生成前にupdateが走ってしまうため
        time.sleep(2)
        self.output_text = self.output_text + "\n" + val
        if self.output_text_area is not None:
            self.output_text_area.update(self.output_text)

    def is_disable_ui(self):
        return self.disable_ui

if __name__ == "__main__":
    
    gui = Gui()
    gui.show_setting()