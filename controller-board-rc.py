import os
import sys
import json
import pathlib
import argparse

import stationrc.common
import stationrc.remote_control
import stationrc.bbb

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
if stationrc.bbb.on_bbb():
    controller = stationrc.bbb.ControllerBoard("/dev/ttyController")
    print(controller.run_command(args.command, read_response = True))
    controller.shut_down()
else:
    for host in args.hosts:
        station = stationrc.remote_control.VirtualStation(host=host)
        print(station.rc.send_command("controller-board", args.command))
