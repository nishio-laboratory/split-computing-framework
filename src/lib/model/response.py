#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import base64
import json
import pickle

class CommonResponse:
    def __init__(self, code, request_id, message="", payload=None):
        self.__code = code
        self.__request_id = request_id
        self.__message = message
        self.__payload = payload

    @property
    def request_id(self):
        return self.__request_id

    @property
    def message(self):
        return self.__message

    @property
    def payload(self):
        return self.__payload

    def get_json(self):
        encoded_payload = ""
        if self.__payload is not None:
            encoded_payload = base64.b64encode(pickle.dumps(self.__payload)).decode(
                "utf-8"
            )
        to_json_data = {
            "code": self.__code,
            "request_id": self.__request_id,
            "message": self.__message,
            "payload": encoded_payload,
        }
        return json.dumps(to_json_data)

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        if "code" not in data:
            raise ValueError("code not found in json")
        if "request_id" not in data:
            raise ValueError("request_id not found in json")
        if "message" not in data:
            raise ValueError("message not found in json")
        if "payload" not in data:
            raise ValueError("payload not found in json")
        return CommonResponse(
            data["code"],
            data["request_id"],
            data["message"],
            pickle.loads(base64.b64decode(bytes(data["payload"].encode()))),
        )


class IotDeviceSettingResponse:
    def __init__(self, model, layer, split_mode, split_size, loss_rate):
        self.__model = model
        self.__layer = layer
        self.__split_mode = split_mode
        self.__split_size = split_size
        self.__loss_rate = loss_rate

    @property
    def model(self):
        return self.__model

    @property
    def layer(self):
        return self.__layer

    @property
    def split_mode(self):
        return self.__split_mode

    @property
    def split_size(self):
        return self.__split_size

    @property
    def loss_rate(self):
        return self.__loss_rate

    def get_json(self):
        to_json_data = {
            "model": self.__model,
            "layer": self.__layer,
            "split_size": self.__split_size,
            "loss_rate": self.__loss_rate,
            "split_mode": self.__split_mode,
        }
        return json.dumps(to_json_data)

    def __str__(self):
        return "model = {}, layer = {}, split_mode = {}, split_size = {}, loss_rate = {}".format(
            self.__model,
            self.__layer,
            self.__split_mode,
            self.__split_size,
            self.__loss_rate,
        )


class EdgeServerSettingResponse:
    def __init__(self, model, layer, split_mode, reach_rate, waiting_time):
        self.__model = model
        self.__layer = layer
        self.__split_mode = split_mode
        self.__reach_rate = reach_rate
        self.__waiting_time = waiting_time

    @property
    def model(self):
        return self.__model

    @property
    def layer(self):
        return self.__layer

    @property
    def split_mode(self):
        return self.__split_mode

    @property
    def reach_rate(self):
        return self.__reach_rate

    @property
    def waiting_time(self):
        return self.__waiting_time

    def get_json(self):
        to_json_data = {
            "model": self.__model,
            "layer": self.__layer,
            "split_mode": self.__split_mode,
            "reach_rate": self.__reach_rate,
            "waiting_time": self.__waiting_time,
        }
        return json.dumps(to_json_data)

    def __str__(self):
        return "model = {}, layer = {}, split_mode = {}, reach_rate = {}, waiting_time = {}".format(
            self.__model,
            self.__layer,
            self.__split_mode,
            self.__reach_rate,
            self.__waiting_time,
        )


# NOTE: CommonResponseのpayloadに直接URLを格納すれば以下のクラスは不要
class CnnModelResponse:
    def __init__(self, url):
        self.__url = url

    @property
    def url(self):
        return self.__url

    def __str__(self):
        return "url = {}".format(self.__url)
