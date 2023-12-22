#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import os
import pickle
import numpy as np
from src.conf import environment_settings

class Compressor:
    QUBIT_NON_COMPRESSION = 'Non compression'
    QUBIT_16BIT_INT = '16bit'
    QUBIT_8BIT_INT = '8bit'
    QUBIT_NORMALIZE_16BIT_INT = 'Normalize 16bit'
    QUBIT_NORMALIZE2SIGMA_16BIT_INT = 'Normalize 2Sigma 16bit'

    def __init__(self):
        self.compress_16bit_int_func = np.frompyfunc(self.compress_16bit_int, 1, 1)
        self.compress_normalize_16bit_int_func = np.frompyfunc(self.compress_normalize_16bit_int, 3, 1)
        self.compress_normalize2sigma_16bit_int_func = np.frompyfunc(self.compress_normalize2sigma_16bit_int, 3, 1)
        self.extract_16bit_int_func = np.frompyfunc(self.extract_16bit_int, 1, 1)
        self.compress_8bit_int_func = np.frompyfunc(self.compress_8bit_int, 1, 1)
        self.extract_8bit_int_func = np.frompyfunc(self.extract_8bit_int, 1, 1)
        # NOTE: 4bit int 以下はPython、numpy両方に型がないため実装する場合は独自実装が必要

    @staticmethod
    def qubit_pattern():
        return [
            Compressor.QUBIT_NON_COMPRESSION,
            Compressor.QUBIT_16BIT_INT,
            Compressor.QUBIT_8BIT_INT,
            Compressor.QUBIT_NORMALIZE_16BIT_INT,
            Compressor.QUBIT_NORMALIZE2SIGMA_16BIT_INT,
        ]


    def compress_16bit_int(self, val):
        compressed = np.array([(val * environment_settings.DEFAULT_16BIT_SCALE)], dtype=np.uint16)
        if compressed[0] < 0:
            return 0
        return compressed[0]

    def compress_nparray_16bit_int(self, nparray_val):
        return self.compress_16bit_int_func(nparray_val)

    def compress_normalize_16bit_int(self, val, max, min):
        # 正規化
        x = (1 / (max - min)) * val
        compressed = np.array([(x * environment_settings.DEFAULT_NORMALIZE_16BIT_SCALE)], dtype=np.uint16)

        # PCA圧縮時にマイナスが発生するためコメントアウト
        # if compressed[0] < 0:
        #     return 0
        return compressed[0]

    def compress_nparray_normalize_16bit_int(self, nparray_val):
        return self.compress_normalize_16bit_int_func(nparray_val, nparray_val.max(), nparray_val.min())

    def compress_normalize2sigma_16bit_int(self, val, median, std):
        # 正規化
        lower = 0
        if 0 < median - (2 * std):
            lower = median - (2 * std)
        upper = median + (2 * std)
        if (val < lower) or (upper < val):
            return 0
        x = (1 / (upper - lower)) * val
        compressed = np.array([(x * environment_settings.DEFAULT_NORMALIZE_16BIT_SCALE)], dtype=np.uint16)

        # PCA圧縮時にマイナスが発生するためコメントアウト
        # if compressed[0] < 0:
        #     return 0
        return compressed[0]

    def compress_nparray_normalize2sigma_16bit_int(self, nparray_val):
        # 1次元にして中央値を算出する
        reshaped = np.sort(nparray_val.reshape(1, np.prod(nparray_val.shape)))
        print("max = {}, min = {}, median = {}, std = {}".format(nparray_val.max(), nparray_val.min(), np.median(reshaped), nparray_val.std()))
        return self.compress_normalize2sigma_16bit_int_func(nparray_val, np.median(reshaped), nparray_val.std())

    def extract_int(self, val, scale):
        extract_raw = (np.array(val)).astype(np.float32)
        return extract_raw / scale

    def extract_16bit_int(self, val):
        return self.extract_int(val, environment_settings.DEFAULT_16BIT_SCALE)
    
    def extract_nparray_16bit_int(self, nparray_val):
        return self.extract_16bit_int_func(nparray_val)


    def compress_8bit_int(self, val):
        compressed = np.array([(val * environment_settings.DEFAULT_8BIT_SCALE)], dtype=np.uint8)
        if compressed[0] < 0:
            return 0
        return compressed[0]

    def compress_nparray_8bit_int(self, nparray_val):
        return self.compress_8bit_int_func(nparray_val)

    def extract_8bit_int(self, val):
        return self.extract_int(val, environment_settings.DEFAULT_8BIT_SCALE)
    
    def extract_nparray_8bit_int(self, nparray_val):
        return self.extract_8bit_int_func(nparray_val)


    def compress_pca(self, val, rate, model, layer):
        print('============================')
        pca_model = self.load_pca_model(model, layer)
        transformed = pca_model.exec_transform(val, rate)
        print(transformed)
        print('============================')
        return transformed

    def extract_pca(self, val, model, layer):
        print('============================')
        pca_model = self.load_pca_model(model, layer)
        inversed = pca_model.exec_inverse_transform(val)
        print(inversed)
        print('============================')
        return inversed

    def load_pca_model(self, model, layer):
        loaded_model = None
        try:
            pca_model_path = os.path.dirname(__file__) + '/saved_model/pca'
            if 'my_model' in model:
                pca_model_path += '/my_model/' + str(layer) + '/saved_model.pb'
            elif 'model_COMtune' in model:
                pca_model_path += '/model_COMtune/' + str(layer) + '/saved_model.pb'
            else:
                raise Exception('pca model not found')
            
            f = open(pca_model_path, 'rb')
            loaded_model = pickle.load(f)
            f.close()
            if loaded_model == None:
                raise Exception('pca model not found')
            return loaded_model
        except Exception as e:
            raise e