#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import unittest

from src.iot_device.iot_device import IotDevice


class TestIotDevice(unittest.TestCase):
    def test_iot_device(self):
        iot_device = IotDevice()
        iot_device.main()

if __name__ == "__main__":
    unittest.main()