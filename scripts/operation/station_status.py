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

if not station.rc.run_local:
    data = station.get_controller_board_monitoring()
    print(data)
else:
    print("Local run: No controller board access -> no monitoring data")

data = station.get_radiant_board_id()
print(data)
