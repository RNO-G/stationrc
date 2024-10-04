import os
import sys
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
    print(stationrc.bbb.ControllerBoard.run_command_controller_board(args.command, read_response = True))    
else:
    for host in args.hosts:
        station = stationrc.remote_control.VirtualStation(host=host)

        data = station.rc.send_command("controller-board", args.command)
        print(data)
