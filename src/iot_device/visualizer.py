#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import numpy as np
import os
import shutil
import time
import threading
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import PySimpleGUI as sg
from PIL import Image
import io
import cv2

from src.conf import visualizer_settings as settings
from src.lib.logger import create_logger

class Visualiser:
    def __init__(self) -> None:
        self.logger = create_logger(__name__)
        self.image_counter = 0
        self.visualize_target_img_directory = '../iot_device/data/visualize_target'
        self.save_dir = '../iot_device/data/visualize'
        self.target_path = settings.TARGET_NUMPY_FILE
        self.window = None
        self.rows = []
        self.is_loading = False
        self.do_continue = True
        self.target_mtime = None
        self.called_close = False
        self.called_update = False
        self.np_layout = None


    def save_visualization(self, data):
        # MNISTの場合はnumpyのそれぞれのデータの型が異なるので、int64型に変換
        # data = data.astype(np.int64)

        # numpy全体の最小値と最大値を取得
        global_min = np.min(data)
        global_max = np.max(data)

        if os.path.exists(self.save_dir):
            shutil.rmtree(self.save_dir)
        os.makedirs(self.save_dir, exist_ok=True)

        # データの形状から層数を取得
        num_layers = data.shape[-1]
        # YOLOv7デモの中間層出力のチャネルが2番目のため直打ち
        num_layers = 8

        for i in range(num_layers):
            # YOLOv7デモの場合は2番目のチャネルで描画
            layer = data[0, i, :, :]
            # MNISTの場合は以下のインデックス指定
            # layer = data[0, :, :, i]

            # 画像のプロット（1層ずつ）
            fig, ax = plt.subplots(figsize=(5, 5))
            # fig, ax = plt.subplots(figsize=(1, 1))
            # vminとvmaxを指定して色の範囲を固定
            ax.imshow(layer, cmap='hot', interpolation='nearest', vmin=global_min, vmax=global_max)
            ax.axis('off')  # 軸を非表示にする

            # 画像の保存（連番を付与）
            save_path = os.path.join(self.save_dir, f'{self.image_counter}.png')

            # 画像のリサイズ
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0)
            buf.seek(0)
            im = Image.open(buf)
            im_resized = im.resize((settings.NUMPY_VISUALIZER_IMAGE_WIDTH, settings.NUMPY_VISUALIZER_IMAGE_HEIGHT))
            im_resized.save(save_path)
            buf.close()

            plt.close()

            self.image_counter += 1

    def np_analyze(self):
        data = np.load(self.target_path, allow_pickle=True)
        self.save_visualization(data)
        self.called_update = True
        self.np_layout = self.prepare_window()

    def execute(self):
        layout = self.prepare_window()
        self.window = sg.Window('Image Viewer', layout, resizable=True, finalize=True)
        while True:
            event, values = self.window.read()
            self.logger.info('event = ' + str(event) + ', values = ' + str(values))
            # なぜか初回の✕ボタンではeventがNoneになるため入れておく
            if event == None or event == sg.WIN_CLOSED or event == 'close' or event == '-CLOSE-':
                self.do_continue = False
                self.logger.info('event WIN_CLOSED')
                self.window.close()
                break
            elif event == '-UPDATE-':
                self.logger.info('event -UPDATE-')
                # ローディングウィンドウを作成
                layout_loading = [[sg.Text('Loading', key='-LOADING_TEXT-')]]
                loading_window = sg.Window('Loading', layout_loading, no_titlebar=True, keep_on_top=True, modal=True, finalize=True)

                # メインウィンドウを一時的に閉じる
                self.window.close()

                # numpyファイル解析処理を別スレッドで実行
                np_analyze_thread = threading.Thread(target=self.np_analyze)
                np_analyze_thread.start()

                loading_text = 'Loading'
                count = 0

                # numpyファイル解析処理スレッドが終了するまでローディングアニメーションを表示
                while np_analyze_thread.is_alive():
                    event, values = loading_window.read(timeout=500)
                    if event == sg.WINDOW_CLOSED:
                        break

                    count = (count + 1) % 4
                    loading_window['-LOADING_TEXT-'].update(loading_text + '.' * count)

                # ローディングウィンドウを閉じる
                loading_window.close()

                # 新しいメインウィンドウを作成
                self.window = sg.Window('Image Viewer', self.np_layout, resizable=True, finalize=True)
                self.window.read()

    def prepare_window(self):
        # 前回の解析画像データがあるとエラーになる場合があるので、起動時は更新ボタンのみのwindowを表示する
        if self.called_update == False:
            layout = [
                [sg.Button('update', key='-UPDATE-'), sg.Button('close', key='-CLOSE-')],
                [sg.Column([], size=(settings.NUMPY_VISUALIZER_WINDOW_WIDTH, settings.NUMPY_VISUALIZER_WINDOW_HEIGHT))],
            ]
            return layout
        self.called_update = False
        img_files = [os.path.join(self.visualize_target_img_directory, f) for f in os.listdir(self.visualize_target_img_directory) if f.endswith('.png')]
        # 中間層出力と並べて出す画像をリサイズ
        orig_img = cv2.imread(img_files[0])
        resized_image = cv2.resize(orig_img, (settings.NUMPY_VISUALIZER_IMAGE_WIDTH, settings.NUMPY_VISUALIZER_IMAGE_HEIGHT))
        cv2.imwrite(img_files[0], resized_image)

        img_files += sorted([os.path.join(self.save_dir, f) for f in os.listdir(self.save_dir) if f.endswith('.png')])

        images_per_row = settings.NUMPY_VISUALIZER_WINDOW_WIDTH // (settings.NUMPY_VISUALIZER_IMAGE_WIDTH + 20)

        def create_image_row(files):
            row = []
            for f in files:
                # img_filesの最初の要素は解析対象画像が入るので、番号ではなくorgという文字列を表示する
                text_label = 'org' if img_files.index(f) == 0 else str(img_files.index(f))
                col = [
                    [sg.Text(text_label)],
                    [sg.Image(filename=f)]
                ]
                row.append(sg.Column(col, vertical_alignment='center'))
            return row

        grouped_files = [img_files[i:i + images_per_row] for i in range(0, len(img_files), images_per_row)]
        self.rows = [create_image_row(group) for group in grouped_files]

        layout = [
            [sg.Button('update', key='-UPDATE-'), sg.Button('close', key='-CLOSE-')],
            [sg.Column(
                self.rows,
                scrollable=True ,
                vertical_scroll_only=True,
                size=(settings.NUMPY_VISUALIZER_WINDOW_WIDTH, settings.NUMPY_VISUALIZER_WINDOW_HEIGHT),
                key='-CONTENT-'
            )],
        ]
        return layout

if __name__ == "__main__":
    visualiser = Visualiser()
    visualiser.execute()
