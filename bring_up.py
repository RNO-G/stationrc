import json

import stationrc.common
import stationrc.remote_control
import argparse


parser = argparse.ArgumentParser()
parser.add_argument(
    "-v",
    "--version",
    type=int,
    default=3,
    help="Specify version number of config file for CPLDs. Default: 3",
)

parser.add_argument(
    "-l",
    "--enable_remote_logger",
    action="store_true",
    help="Enable remote loggert",
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

if args.enable_remote_logger:
    station.rc.set_remote_logger_handler()

station.radiant_setup(version=args.version)
with open(f"peds_{station.get_radiant_board_mcu_uid():032x}.json", "w") as f:
    json.dump(station.radiant_pedestal_get(), f)
