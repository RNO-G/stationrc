from stationrc.bbb.controller_board import ControllerBoard, check_if_controller_console_is_open

import sys
import json
import pathlib


def power_cycle_radiant():
    if check_if_controller_console_is_open():
            sys.exit("Controller console is open. Please close it before running this script.")

    conf_file = pathlib.Path(__file__).parent / "conf" / "station_conf.json"
    with open(conf_file, "r") as f:
        station_conf = json.load(f)

    controller_board = ControllerBoard(
        uart_device=station_conf["daq"]["controller_board_dev"],
        uart_baudrate=station_conf["daq"]["controller_board_baudrate"]
    )

    print(controller_board.run_command("#RADIANT-OFF"))
    print(controller_board.run_command("#RADIANT-ON"))

    controller_board.shut_down()