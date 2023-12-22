#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

class _code:
    SUCCESS = 0
    SUFFICIENT_DATA_ARRIVAL = 1
    TIME_EXCEEDED = 2
    ERROR_JSON_FORMAT = 100

    class ConstError(TypeError):
        pass

    def __setattr__(self, name, value):
        if name in self.__dict__:
            raise self.ConstError("Can't rebind code (%s)" % name)
        self.__dict__[name] = value


import sys

sys.modules[__name__] = _code()
