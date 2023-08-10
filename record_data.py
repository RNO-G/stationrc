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
    help="Plot certain channel. If None plot all channels. (Default: None)",
)
parser.add_argument(
    "-u",
    "--use_UART",
    action="store_true",
    help="Use UART, not GPIO to check for events",
)
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.daq_record_data(
    num_events=args.num_events, force_trigger=True, use_uart=args.use_UART
)

for ev in data["data"]["WAVEFORM"]:
    fig = plt.figure()
    ax = fig.subplots()
    if args.channel is None:
        for ch, wvf in enumerate(ev["radiant_waveforms"]):
            ax.plot(wvf, label=f"ch. {ch}")
    else:
        ax.plot(ev["radiant_waveforms"][args.channel], label=f"ch. {args.channel}")

    ax.legend()
    ax.set_title(f"Event: {ev['event_number']}")
    ax.set_xlabel("Sample")
    ax.set_ylabel("ADC counts")
plt.show()
