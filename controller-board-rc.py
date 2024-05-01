import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument("command", type=str, help="command to be sent to station")

parser.add_argument(
    "--host", "--hosts",
    dest="hosts",
    type=str, default=[None],
    nargs="+",
    help="Specify ip address of host. If `None`, use ip from config in stationrc.")


args = parser.parse_args()

stationrc.common.setup_logging()

for host in args.hosts:
    station = stationrc.remote_control.VirtualStation(host=host)

    data = station.rc.send_command("controller-board", args.command)
    print(data)
