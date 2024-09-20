from stationrc.bbb.ControllerBoard import ControllerBoard
import stationrc.remote_control
import stationrc.common

import os
import json
import pathlib
import argparse


stationrc.common.setup_logging()

# Determine if we are running on the BeagleBone Black
on_bbb = os.path.exists("/dev/ttyRadiant")

if on_bbb:

    conf_file = pathlib.Path(__file__).parent / "stationrc" / "bbb" / "conf" / "station_conf.json"
    with open(conf_file, "r") as f:
        station_conf = json.load(f)

    controller_board = ControllerBoard(
        uart_device=station_conf["daq"]["controller_board_dev"],
        uart_baudrate=station_conf["daq"]["controller_board_baudrate"]
    )

    print(controller_board.run_command("#RADIANT-OFF"))
    print(controller_board.run_command("#RADIANT-ON"))

    controller_board.shut_down()

else:

    parser = argparse.ArgumentParser()
    parser.add_argument("command", type=str, help="command to be sent to station")

    parser.add_argument(
        "--host", "--hosts",
        dest="hosts",
        type=str, default=[None],
        nargs="+",
        help="Specify ip address of host. If `None`, use ip from config in stationrc.")


    args = parser.parse_args()

    for host in args.hosts:
        station = stationrc.remote_control.VirtualStation(host=host)

        data = station.rc.send_command("controller-board", "#RADIANT-OFF")
        print(data)
        data = station.rc.send_command("controller-board", "#RADIANT-ON")
        print(data)