#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

class _command:
    # クラウドサーバーへのリクエストコマンド群
    # IoTデバイスコマンド群
    IOT_GET_SETTING = 1100
    IOT_GET_CNN_MODEL = 1101
    IOT_GET_INFERENCE_TARGET = 1110
    IOT_SEND_PROCESS_TIME = 1111
    EDGE_GET_SETTING = 1200
    EDGE_GET_CNN_MODEL = 1201
    EDGE_SEND_INFERENCE_RESULT = 1210
    EDGE_SEND_PROCESS_TIME = 1211
    CLOUD_END = 1999

    # エッジサーバーへのリクエストコマンド群
    IOT_SEND_RESULT_SUMMARY = 2000
    IOT_SEND_RESULT_DATA = 2010
    CLOUD_SEND_SETTING_TO_EDGE = 2110
    EDGE_END = 2999

    # IoTデバイスへのリクエストコマンド群
    EDGE_SEND_RECEIVED_RESULT = 3000
    CLOUD_SEND_SETTING_TO_IOT = 3001
    IOT_SEND_PROCESS_TIME = 3211
    IOT_END = 3999

    class ConstError(TypeError):
        pass

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("Can't rebind const (%s)" % name)
        self.__dict__[name] = value


import sys

sys.modules[__name__] = _command()
