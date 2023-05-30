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
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.daq_record_data(num_events=args.num_events, force_trigger=True)

for ev in data["data"]["WAVEFORM"]:
    fig = plt.figure()
    ax = fig.subplots()
    for ch, wvf in enumerate(ev["radiant_waveforms"]):
        ax.plot(wvf, label=f"ch. {ch}")
    ax.legend()
    ax.set_title(f"Event: {ev['event_number']}")
    ax.set_xlabel("Sample")
    ax.set_ylabel("ADC counts")
plt.show()
