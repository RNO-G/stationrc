import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()

parser.add_argument(
    "--host",
    type=str,
    default=None,
    nargs="?",
    help="Specify host. If None (default) take what ever is in "
         "`stationrc/remote_control/conf/virtual_station_conf*.json`"
)

args = parser.parse_args()
stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(host=args.host)
station.radiant_sig_gen_off()
station.radiant_calselect(quad=None)
