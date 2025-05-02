import argparse

import stationrc.common
import stationrc.remote_control
import stationrc.remote_control.tune


parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--channel",
    type=int,
    nargs="+",
    choices=[ch for ch in range(24)],
    default=[ch for ch in range(24)],
    help="channels for tuning",
)
parser.add_argument("--reset", action="store_true", help="reset LAB4Ds")
parser.add_argument("--reset_radiant", action="store_true", help="Reset Radiant")

parser.add_argument(
    "-f",
    "--frequency",
    type=float,
    default=510,
    help="Specify tuning frequency. The band is choosen automatically. Default: 510 MHz",
)

parser.add_argument(
    "--max_iterations",
    type=int,
    default=50,
    help="Maximum number of iterations in each tuning step. Default: 50",
)


parser.add_argument(
    "-e",
    "--external",
    action="store_true",
    help="Use external signal",
)

parser.add_argument(
    "--tune-mean",
    dest="tune_with_mean",
    action="store_true",
    help="Skip tuning loop which usese the mean of samples as seam proxy.",
)

parser.add_argument(
    "-q",
    "--quad",
    "--quads",
    dest="quads",
    type=int,
    nargs="+",
    choices=[q for q in range(3)],
    default=[q for q in range(3)],
    help="Quads for tuning"
)

parser.add_argument(
    "-a",
    "--average",
    action="store_true"
)

parser.add_argument(
    "--exclude_channels",
    type=int,
    nargs="+",
    default=[]
)

parser.add_argument(
    "--host",
    type=str,
    default=None,
    help="Specify ip address of host. If `None`, use ip from `virtual_station_config.json`."
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(load_calibration=True, host=args.host)

stationrc.remote_control.tune.main(station, args)