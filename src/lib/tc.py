#!/usr/bin/env python3
# -*- Coding: utf-8 -*-
import sys
import subprocess
from src.lib.logger import create_logger

class Tc:
    @staticmethod
    def execute_tc(device, network_delay_time, network_dispersion_time, network_loss_rate, network_band_limitation):
        logger = create_logger(__name__)
        logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        logger.info(
            "device = {}, network_delay_time = {}, network_dispersion_time = {}, network_loss_rate = {}, network_band_limitation = {}".format(
                device,
                network_delay_time,
                network_dispersion_time,
                network_loss_rate,
                network_band_limitation
            )
        )
        cmd_tc_add = "tc qdisc add dev {} root handle 1:0".format(device).split()

        cmd_tc_netem = ["netem"]
        if network_delay_time != 0.0:
            cmd_tc_netem.extend(["delay", str(network_delay_time) + "ms"])
            if network_dispersion_time != 0:
                cmd_tc_netem.extend([str(network_dispersion_time) + "ms"])
        if network_loss_rate != 0:
            cmd_tc_netem.extend(["loss", str(network_loss_rate * 100) + "%"])
        if network_band_limitation != 0:
            # NOTE: burst指定するとエラーになるため計算したが未使用
            burst = (network_band_limitation * (10 ** 6 )) / (8 * 10)
            # formatted_burst = str(int(burst / 10 ** 3)) + "kb"
            # band_limitation_cmd = "rate {} burst {} latency 70ms".format(formatted_band_limitation, formatted_burst)
            formatted_band_limitation = str(network_band_limitation) + "mbit"
            band_limitation_cmd = "rate {} ".format(formatted_band_limitation)
            cmd_tc_netem.extend(band_limitation_cmd.split())
            
        if network_delay_time != 0.0 or network_loss_rate != 0.0 or network_band_limitation != 0.0:  # どちらも設定が0などの場合はtcコマンドを実行しない    
            cmd_tc_add.extend(cmd_tc_netem)
            res = subprocess.run(cmd_tc_add, stderr=subprocess.PIPE)
            if res.returncode != 0: # subprocess.run(cmd_tc_add)が失敗したら
                cmd_tc_change = "tc qdisc change dev {} root handle 1:0".format(device).split()
                cmd_tc_change.extend(cmd_tc_netem)
                logger.info(cmd_tc_change)
                subprocess.run(cmd_tc_change)
        logger.info(f"====== end {sys._getframe().f_code.co_name} ======")

    @staticmethod
    def reset_tc(device, network_delay_time, network_dispersion_time, network_loss_rate, network_band_limitation):
        logger = create_logger(__name__)
        logger.info(f"===== start {sys._getframe().f_code.co_name} =====")
        logger.info(
                "device = {}, network_delay_time = {}, network_dispersion_time = {}, network_loss_rate = {}, network_band_limitation = {}".format(
                device,
                network_delay_time,
                network_dispersion_time,
                network_loss_rate,
                network_band_limitation
            )
        )
        if network_delay_time != 0.0 or network_loss_rate != 0.0 or network_band_limitation != 0.0:
            cmd_tc_change = "tc qdisc del dev {} root".format(device).split()
            subprocess.run(cmd_tc_change)
        else:
            logger.info(f"tc reset unneeded.")
        logger.info(f"====== end {sys._getframe().f_code.co_name} ======")
