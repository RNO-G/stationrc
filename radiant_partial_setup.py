"""
Run selected steps of the RADIANT setup (see `stationrc.radiant.setup_radiant`), e.g., to
only program the CPLDs to heat up the RADIANT with limited power.

Steps (in this order): cplds, analog, lab4. Running all three equals `bring_up.py`.
"""
import argparse
import sys

import stationrc.common
import stationrc.remote_control


STEPS = ["cplds", "analog", "lab4"]

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument(
    "steps",
    nargs="+",
    choices=STEPS,
    help="Setup steps to run (always executed in the order cplds, analog, lab4).",
)
parser.add_argument(
    "-v",
    "--version",
    type=int,
    default=3,
    help="Specify version number of config file for CPLDs. Default: 3",
)
parser.add_argument(
    "--labs",
    type=int,
    nargs="+",
    choices=range(24),
    default=None,
    metavar="LAB",
    help="Step lab4: only initialize these LABs (0-23); the others get zero pedestals. "
         "Default: all LABs. Give the steps before this option.",
)
parser.add_argument(
    "--no-pedestals",
    dest="pedestals",
    action="store_false",
    help="Step lab4: do not take pedestals.",
)
parser.add_argument(
    "--host",
    type=str,
    default=None,
    help="Specify ip address of host. If `None`, use ip from config in stationrc.",
)
args = parser.parse_args()

if "lab4" not in args.steps and (args.labs is not None or not args.pedestals):
    parser.error("--labs and --no-pedestals require the step lab4.")

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(host=args.host)

functions = {
    "cplds": lambda: station.radiant_program_cplds(version=args.version),
    "analog": station.radiant_analog_setup,
    "lab4": lambda: station.radiant_lab4_setup(labs=args.labs, pedestals=args.pedestals),
}

try:
    for step in STEPS:
        if step in args.steps:
            functions[step]()
except KeyboardInterrupt:
    sys.exit()
