#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import json
import uuid
import datetime
T_DELTA = datetime.timedelta(hours=9)

class CommonRequest:
    def __init__(self, command, request_id=str(uuid.uuid4())):
        self.data = None
        self.__command = command
        self.__request_id = request_id

    @property
    def request_id(self):
        return self.__request_id

    @property
    def command(self):
        return self.__command

    def get_json(self):
        dump_object = (
            self.data
            if self.data is not None
            else {"command": self.__command, "request_id": self.__request_id}
        )
        return json.dumps(dump_object)

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        if "command" not in data:
            raise ValueError("command not found in json")
        if "request_id" not in data:
            raise ValueError("request_id not found in json")
        return CommonRequest(data["command"], data["request_id"])

    def __repr__(self) -> str:
        return self.get_json()

class CnnModelRequest(CommonRequest):
    def __init__(self, command, model, request_id=str(uuid.uuid4())):
        super(CnnModelRequest, self).__init__(command, request_id)
        self.__model = model

    @property
    def model(self):
        return self.__model

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "model": self.model,
        }
        return super(CnnModelRequest, self).get_json()

class IotDeviceResultSummaryRequest(CommonRequest):
    def __init__(
        self,
        command,
        num_packets,
        num_elements,
        random_seed,
        filename='',
        shape=None,
        request_id=str(uuid.uuid4()),
    ):
        super(IotDeviceResultSummaryRequest, self).__init__(command, request_id)
        self.__num_packets = num_packets
        self.__num_elements = num_elements
        self.__random_seed = random_seed
        self.__filename = filename
        self.__shape = shape

    @property
    def num_packets(self):
        return self.__num_packets

    @property
    def num_elements(self):
        return self.__num_elements

    @property
    def random_seed(self):
        return self.__random_seed

    @property
    def filename(self):
        return str(self.__filename)
    
    @property
    def shape(self):
        return self.__shape

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "num_packets": self.num_packets,
            "num_elements": self.num_elements,
            "random_seed": self.random_seed,
            "filename": self.filename,
            "shape": self.shape
        }
        return super(IotDeviceResultSummaryRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return IotDeviceResultSummaryRequest(
                data["command"],
                data["num_packets"],
                data["num_elements"],
                data["random_seed"],
                data["filename"],
                data["shape"],
                data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)


#
class IotDeviceResultDataRequest(CommonRequest):
    def __init__(self, command, payload, sequence, request_id=str(uuid.uuid4())):
        super(IotDeviceResultDataRequest, self).__init__(command, request_id)
        self.__payload = payload
        self.__sequence = sequence

    @property
    def payload(self):
        return self.__payload

    @property
    def sequence(self):
        return self.__sequence

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "payload": self.payload,
            "sequence": self.sequence,
        }
        return super(IotDeviceResultDataRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return IotDeviceResultDataRequest(
                data["command"], data["payload"], data["sequence"], data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)

class EdgeServerReceivedResultRequest(CommonRequest):
    def __init__(self, command, code, request_id=str(uuid.uuid4())):
        super(EdgeServerReceivedResultRequest, self).__init__(command, request_id)
        self.__code = code

    @property
    def code(self):
        return self.__code

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "code": self.code,
        }
        return super(EdgeServerReceivedResultRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return EdgeServerReceivedResultRequest(
                data["command"], data["code"], data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)


class EdgeServerInferenceResultRequest(CommonRequest):
    def __init__(self, command, result, filename, request_id=str(uuid.uuid4())):
        super(EdgeServerInferenceResultRequest, self).__init__(command, request_id)
        self.__result = result
        self.__filename = filename

    @property
    def result(self):
        return self.__result

    @property
    def filename(self):
        return self.__filename

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "result": self.result,
            "filename": self.filename,
        }
        return super(EdgeServerInferenceResultRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return EdgeServerInferenceResultRequest(
                data["command"], data["result"], data["filename"], data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)

class CloudServerSettingRequest(CommonRequest):
    def __init__(self, command, setting, request_id=str(uuid.uuid4())):
        super(CloudServerSettingRequest, self).__init__(command, request_id)
        self.__setting = setting

    @property
    def setting(self):
        return self.__setting

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "setting": self.setting,
        }
        return super(CloudServerSettingRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return CloudServerSettingRequest(
                data["command"], data["setting"], data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)

class ProcessTimeRequest(CommonRequest):
    def __init__(
        self,
        command,
        process_name,
        process_time = (datetime.datetime.now(datetime.timezone(T_DELTA, 'JST'))).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3],
        request_id=str(uuid.uuid4())
    ):
        super(ProcessTimeRequest, self).__init__(command, request_id)
        self.__process_name = process_name
        self.__process_time = process_time

    @property
    def process_name(self):
        return self.__process_name
    @property
    def process_time(self):
        return self.__process_time

    def get_json(self):
        self.data = {
            "command": self.command,
            "request_id": self.request_id,
            "process_name": self.process_name,
            "process_time": self.process_time,
        }
        return super(ProcessTimeRequest, self).get_json()

    @staticmethod
    def convert_from_json(json_str):
        data = json.loads(json_str)
        try:
            return ProcessTimeRequest(
                data["command"], data["process_name"], data["process_time"], data["request_id"]
            )
        except Exception as e:
            raise AttributeError(e)
