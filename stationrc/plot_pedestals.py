import signal

signal.signal(
    signal.SIGINT, signal.SIG_DFL
)  # allows to close matplotlib window with CTRL+C from terminal

import argparse
import matplotlib.pyplot as plt

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--channel",
    type=int,
    default=None,
    help="Plot certain channel. If None plot all channels. (Default: None)",
)

parser.add_argument(
    "--no_update",
    action="store_true",
    help="If set, do not run updatePedestals()",
)

parser.add_argument(
    "--reset",
    action="store_true",
    help="Reset radiant",
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

if args.reset:
    station.reset_radiant_board()

if not args.no_update:
    station.radiant_pedestal_update()

data = station.radiant_pedestal_get()

fig = plt.figure()
ax = fig.subplots()
if args.channel is None:
    for ch, ped in enumerate(data):
        ax.plot(ped, label=f"ch. {ch}")
else:
    ax.plot(data[args.channel], label=f"ch. {args.channel}")

ax.legend()
ax.set_xlabel("Sample")
ax.set_ylabel("ADC counts")
plt.show()
