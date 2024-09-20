import os
import json
import pathlib
import argparse

import stationrc.common
import stationrc.remote_control
import stationrc.bbb.ControllerBoard

stationrc.common.setup_logging()

parser = argparse.ArgumentParser()
parser.add_argument("command", type=str, help="command to be sent to station")

parser.add_argument(
    "--host", "--hosts",
    dest="hosts",
    type=str, default=[None],
    nargs="+",
    help="Specify ip address of host. If `None`, use ip from config in stationrc.")


args = parser.parse_args()

# Determine if we are running on the BeagleBone Black
on_bbb = os.path.exists("/dev/ttyRadiant")

if on_bbb:

    conf_file = pathlib.Path(__file__).parent / "stationrc" / "bbb" / "conf" / "station_conf.json"
    with open(conf_file, "r") as f:
        station_conf = json.load(f)

    controller_board = stationrc.bbb.ControllerBoard.ControllerBoard(
        uart_device=station_conf["daq"]["controller_board_dev"],
        uart_baudrate=station_conf["daq"]["controller_board_baudrate"]
    )

    print(controller_board.run_command(args.command))

    controller_board.shut_down()

else:
    for host in args.hosts:
        station = stationrc.remote_control.VirtualStation(host=host)

        data = station.rc.send_command("controller-board", args.command)
        print(data)
