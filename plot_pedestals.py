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
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

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
