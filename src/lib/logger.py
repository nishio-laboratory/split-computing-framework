#!/usr/bin/env python3
# -*- Coding: utf-8 -*-

import datetime
import logging
import os

def create_logger(name):
    stream_handler = logging.StreamHandler()

    log_directory = "log/"
    os.makedirs(log_directory, exist_ok=True)
    current_time_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=9))
    ).strftime("%y%m%d_%H%M%S")
    log_file = os.path.join(log_directory, f"{current_time_str}.log")
    file_handler = logging.FileHandler(log_file)

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[stream_handler, file_handler],
    )
    logger = logging.getLogger(name)
    return logger
