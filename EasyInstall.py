#!/bin/python3
import argparse
import json
import platform
import shutil
import git
from colorama import Back

from ESP32Flasher import ESP32Flasher

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s", "--serialport", type=str, help="Define serial port", default=""
    )
    parser.add_argument(
        "-ps", "--preselect", type=int, help="Preselect flashing option", default=None
    )
    args = parser.parse_args()

    flasher = ESP32Flasher()
    flasher.serialport = args.serialport
    flasher.fwchoice = args.preselect

    flasher.prereqcheck()
    flasher.choose_fw()
