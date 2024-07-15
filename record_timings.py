import signal
import numpy as np
import datetime as dt
import argparse
import subprocess

import stationrc.common
import stationrc.remote_control
from stationrc.remote_control.utils import get_channels_for_quad


signal.signal(
    signal.SIGINT, signal.SIG_DFL
)  # allows to close matplotlib window with CTRL+C from terminal


def get_hostname():
    sp = subprocess.run(["hostnamectl", "hostname"], capture_output=True)
    sp.check_returncode()
    return sp.stdout.decode("utf-8").strip('\n')


def record_for_quad(station, quad, args):

    station.radiant_calselect(quad=quad)
    station.radiant_sig_gen_set_frequency(
        frequency=args.frequency
    )

    n_recordings = args.num_recordings

    t = np.squeeze([stationrc.remote_control.get_time_run(
        station=station, frequency=args.frequency * 1e6) for _ in range(n_recordings)])

    if n_recordings > 1:
        # n, channels, samples -> channels, n, samples
        t = np.swapaxes(t, 0, 1)

    return t


parser = argparse.ArgumentParser()
parser.add_argument(
    "-n",
    "--num-recordings",
    dest="num_recordings",
    type=int,
    default=1,
    help="number of recordings to record",
)

parser.add_argument(
    "-f",
    "--frequency",
    type=float,
    default=510,
    help="Frequency for on-board signal generator (in MHz). (Default: 510 MHz)",
)

parser.add_argument(
    "-b",
    "--band",
    type=int,
    default=2,
    help="Filter band for on-board signal generator. (Default: 2)",
)

parser.add_argument(
    "--filename",
    type=str,
    default=None,
    nargs="?"
)

parser.add_argument(
    "--host",
    type=str,
    default=None,
    nargs="?",
    help="Set host",
)

parser.add_argument(
    '-d'
    "--data_dir",
    type=str,
    default="./",
    nargs="?"
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(load_calibration=True, host=args.host)
if station.rc.run_local:
    host = get_hostname()
else:
    host = station.remote_host

station.radiant_sig_gen_off()
station.radiant_sig_gen_configure(
    pulse=False, band=args.band
)
station.radiant_pedestal_update()
station.radiant_sig_gen_on()

timings = {}

for quad in range(3):
    channels = get_channels_for_quad(quad)
    t = record_for_quad(station, quad, args)
    print(t.shape)
    for ch in channels:
        print(ch)
        timings[str(ch)] = t[ch]

date = dt.datetime.now(dt.UTC).strftime("%Y_%m_%d-%H%M")
np.savez(f"{args.data_dir}/timing_{host}_{date}.npz", **timings)
