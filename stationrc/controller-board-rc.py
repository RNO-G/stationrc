import os
import sys
import json
import pprint
import pathlib
import argparse

import stationrc.common
import stationrc.remote_control
import stationrc.bbb

def print_data(data, args):
    if args.command.lower().endswith("monitor"):
        # Pretty print the dictionary
        pprint.pprint(data, width=120, compact=True, indent=2, sort_dicts=False)
    else:
        print(data)

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
    data = controller.run_command(args.command, read_response = True)
    print_data(data, args)
    controller.shut_down()
else:
    for host in args.hosts:
        station = stationrc.remote_control.VirtualStation(host=host)
        data = station.rc.send_command("controller-board", args.command)
        print_data(data, args)
