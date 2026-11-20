import json
import sys
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
    "-p",
    "--pedestals",
    action="store_true",
    help="If true, request and store pedestals.",
)

parser.add_argument(
    "--labs",
    type=int,
    nargs="+",
    choices=range(24),
    default=None,
    metavar="LAB",
    help="Only set up these LABs (0-23); the others get zero pedestals. Default: all LABs.",
)

parser.add_argument(
    "--host", "--hosts",
    dest="hosts",
    type=str, default=[None],
    nargs="+",
    help="Specify ip address of host. If `None`, use ip from config in stationrc.")

args = parser.parse_args()

stationrc.common.setup_logging()

for host in args.hosts:
    station = stationrc.remote_control.VirtualStation(load_calibration=True, host=host)

    try:
        station.radiant_setup(version=args.version, labs=args.labs)
    except KeyboardInterrupt:
        sys.exit()

    if args.pedestals:
        with open(f"peds_{station.get_radiant_board_mcu_uid():032x}.json", "w") as f:
            json.dump(station.radiant_pedestal_get(), f)
