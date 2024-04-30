import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument("command", type=str, help="command to be sent to station")

parser.add_argument(
    "--host",
    type=str,
    default=None,
    help="Specify ip address of host. If `None`, use ip from `virtual_station_config.json`."
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(host=args.host)

data = station.rc.send_command("controller-board", args.command)
print(data)
