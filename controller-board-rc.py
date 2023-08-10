import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument("command", type=str, help="command to be sent to station")
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.rc.send_command("controller-board", args.command)
print(data)
