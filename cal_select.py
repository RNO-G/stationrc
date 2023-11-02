import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)


parser.add_argument(
    "-q",
    "--quad",
    type=int,
    choices=[0, 1, 2],
    default=0,
    help='Quad to connect to the signal generator:'
    "\n\t quad | channel ids"
    "\n\t ------------------"
    "\n\t 0    | 0, 1, 2, 3, 12, 13, 14, 15"
    "\n\t 1    | 4, 5, 6, 7, 16, 17, 18, 19"
    "\n\t 2    | 8, 9, 10, 11, 20, 21, 22, 23\n\n",
)


args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()
station.radiant_calselect(quad=args.quad)
