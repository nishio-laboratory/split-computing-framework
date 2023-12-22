#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import unittest

from src.cloud_server.cloud_server import CloudServer


class TestCloudServer(unittest.TestCase):
    def test_cloud_server(self):
        cloud_server = CloudServer()
        cloud_server.main()

if __name__ == "__main__":
    unittest.main()