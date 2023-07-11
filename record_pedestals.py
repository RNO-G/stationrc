import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)  # allows to close matplotlib window with CTRL+C from terminal

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

parser.add_argument('-u', "--use_UART", action="store_true", help="Use UART, not GPIO to check for events")
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.daq_record_data(num_events=1, force_trigger=True, use_uart=args.use_UART, read_pedestal=True)

for ev in data["data"]["PEDESTAL"]:
    fig = plt.figure()
    ax = fig.subplots()
    if args.channel is None:
        for ch, ped in enumerate(ev["pedestals"]):
            ax.plot(ped, label=f"ch. {ch}")
    else:
        ax.plot(ev["pedestals"][args.channel], label=f"ch. {args.channel}")
        
    ax.legend()
    ax.set_xlabel("Sample")
    ax.set_ylabel("ADC counts")
plt.show()
