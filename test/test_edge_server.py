#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import unittest

from src.edge_server.edge_server import EdgeServer


class TestEdgeServer(unittest.TestCase):
    def test_edge_server(self):
        edge_server = EdgeServer()
        edge_server.main()

if __name__ == "__main__":
    unittest.main()