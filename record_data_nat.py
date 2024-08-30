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
    "-l",
    "--line",
    action="store_true",
    help="Plot vertical lines each 128 samples",
)

parser.add_argument(
    "-m",
    "--marker",
    type=str,
    default="",
    const="o",
    nargs="?",
    help="Set marker",
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

parser.add_argument(
    "-s",
    "--save",
    action="store_true",
    help="Store plots"
)

parser.add_argument(
    "--save_data",
    action="store_true",
    help="Store plots"
)

parser.add_argument(
    "--filename",
    type=str,
    default=None,
    nargs="?"
)

parser.add_argument(
    "--read_windows",
    action="store_true",
    help="Store plots"
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.daq_record_data(
    num_events=args.num_events, force_trigger=False, trigger_channels=[6], use_uart=args.use_UART,
    trigger_threshold=0.9, read_header=args.read_windows,
)

if args.save or args.save_data:
    uid = station.get_radiant_board_mcu_uid()
'''
for idx, ev in enumerate(data["data"]["WAVEFORM"]):
    fig, ax = plt.subplots()
    if args.channel is None:
        for ch, wvf in enumerate(ev["radiant_waveforms"]):
            ax.plot(wvf, marker=args.marker, label=f"ch. {ch}")
    else:
        for channel in args.channel:
            ax.plot(ev["radiant_waveforms"][channel], marker=args.marker, label=f"ch. {channel}", lw=1)

    if args.range is not None:
        if len(args.range) == 1:
            c = np.diff(ax.get_xlim())[0] // 2
            ax.set_xlim(c - args.range[0] // 2, c + args.range[0] // 2)
        elif len(args.range) == 2:
            ax.set_xlim(*args.range)
        else:
            raise ValueError("Wrong length for args.range (only 1 or 2 are allowed)")

    if args.line:
        for i in range(16):
            ax.axvline(i * 128, color="k", lw=1, zorder=0)

    ax.legend()
    ax.set_title(f"Event: {ev['event_number']}")
    ax.set_xlabel("Sample")
    ax.set_ylabel("ADC counts")
    if args.save:
        fig.tight_layout()
        plt.savefig(f"waveform_ch{args.channel}_{idx}_{uid:032x}", transparent=False)

if not args.save and not args.save_data:
    plt.show()
'''

if args.save_data:
    import json

    filename = args.filename or f"testdata/waveform_ch_{uid:032x}"

    if not filename.endswith(".json"):
        filename += ".json"

    if args.read_windows:
        with open(filename, "w") as f:
            if args.channel is None:
                json.dump(data["data"], f)
            else:
                for channel in args.channel:
                    json.dump(data["data"][channel], f)

    else:
        with open(filename, "w") as f:
            if args.channel is None:
                json.dump(data["data"]["WAVEFORM"], f)
            else:
                #This is not a great solution because it only allows for one channel
                for idx, ev in enumerate(data["data"]["WAVEFORM"]):
                    ev["radiant_waveforms"] = ev["radiant_waveforms"][args.channel[0]]
                json.dump(data["data"]["WAVEFORM"], f)
