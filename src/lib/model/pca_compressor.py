#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import numpy as np
from sklearn.decomposition import PCA
from src.lib.logger import create_logger

class PcaCompressor(PCA):
    def __init__(self):
        super(PcaCompressor, self).__init__()

    @property
    def original_shape(self):
        return self.__original_shape

    def set_original_shape_and_fit(self, val):
        self.__original_shape = val.shape
        self.fit(val.reshape(np.prod(self.__original_shape), 1))

    def exec_transform(self, val, compression_rate):
        # 元の次元数をかけ合わせて1次元にするときの軸数を求める
        reshape_dim = np.prod(self.__original_shape)
        reshaped = val.reshape(reshape_dim, 1)
        transformed = self.transform(reshaped)
        # PCA圧縮率から残す次元数を求める
        compressed_dim = int(reshape_dim * compression_rate)
        # PCA圧縮後の次元数が残す次元数を超えている場合は圧縮後の次元数を使う
        if transformed.shape[0] < compressed_dim:
            compressed_dim = transformed.shape[0]
        # 0埋めした配列を作り、
        compressed = np.zeros_like(reshaped)
        # 圧縮後の配列の先頭から順にコピーする
        for idx in range(0, compressed_dim):
            compressed[idx] = transformed[idx]

        return compressed.reshape(self.__original_shape)

    def exec_inverse_transform(self, val):
        # 元の次元数をかけ合わせて1次元にするときの軸数を求める
        reshape_dim = np.prod(self.__original_shape)
        reshaped = val.reshape(reshape_dim, 1)
        inversed = self.inverse_transform(reshaped)
        return inversed.reshape(self.__original_shape)
