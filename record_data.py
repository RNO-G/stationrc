import signal
import numpy as np
signal.signal(
    signal.SIGINT, signal.SIG_DFL
)  # allows to close matplotlib window with CTRL+C from terminal

import argparse
import matplotlib.pyplot as plt

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument(
    "-n",
    "--num-events",
    dest="num_events",
    type=int,
    default=1,
    help="number of events to record",
)
parser.add_argument(
    "-c",
    "--channel",
    type=int,
    default=None,
    nargs="*",
    help="Plot certain channel. If None plot all channels. (Default: None)",
)
parser.add_argument(
    "-u",
    "--use_UART",
    action="store_true",
    help="Use UART, not GPIO to check for events",
)

parser.add_argument(
    "-r",
    "--range",
    type=int,
    nargs="*",
    default=None,
    metavar="int or [int, int]",
    help="Set range (in samples) to plot. Single int: lenght to plot centered around the middle. Two ints: xlow, xup. Default: None -> full range",
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.daq_record_data(
    num_events=args.num_events, force_trigger=True, use_uart=args.use_UART
)

for ev in data["data"]["WAVEFORM"]:
    fig, ax = plt.subplots()
    if args.channel is None:
        for ch, wvf in enumerate(ev["radiant_waveforms"]):
            ax.plot(wvf, label=f"ch. {ch}")
    else:
        for channel in args.channel:
            ax.plot(ev["radiant_waveforms"][channel], label=f"ch. {channel}")

    if args.range is not None:
        if len(args.range) == 1:
            c = np.diff(ax.get_xlim())[0] // 2
            ax.set_xlim(c - args.range[0] // 2, c + args.range[0] // 2)
        elif len(args.range) == 2:
            ax.set_xlim(*args.range)
        else:
            raise ValueError("Wrong length for args.range (only 1 or 2 are allowed)")

    ax.legend()
    ax.set_title(f"Event: {ev['event_number']}")
    ax.set_xlabel("Sample")
    ax.set_ylabel("ADC counts")
plt.show()
