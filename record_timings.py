import signal
import numpy as np
import datetime as dt
import argparse
import subprocess
import logging

import stationrc.common
import stationrc.remote_control
from stationrc.remote_control.utils import get_channels_for_quad
import os

signal.signal(
    signal.SIGINT, signal.SIG_DFL
)  # allows to close matplotlib window with CTRL+C from terminal


def get_date_of_calibration_file(station):

    directory = os.path.dirname(__file__)

    file_name = f"cal_{station.radiant_low_level_interface.board_manager_uid():032x}.json"
    calib_file = os.path.join(directory, "calib", file_name)

    if os.path.exists(calib_file):
        return dt.datetime.fromtimestamp(os.path.getmtime(calib_file)).astimezone(dt.UTC).timestamp()

    return None


def get_hostname():
    try:
        sp = subprocess.run(["hostnamectl", "hostname"], capture_output=True)
        sp.check_returncode()
    except subprocess.CalledProcessError:
        # Necessary for station 24 with old bbb
        sp = subprocess.run(["hostnamectl", "| grep hostname", "| awk '{print $3}'"], capture_output=True)
        sp.check_returncode()

    return sp.stdout.decode("utf-8").strip('\n')


def record_for_quad(station, quad, n_recordings):

    station.radiant_calselect(quad=quad)

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
    "-d",
    "--data_dir",
    dest="data_dir",
    type=str,
    default="./",
    nargs="?"
)

parser.add_argument(
    "--load_calibration",
    action="store_true",
    help="Load the calibration. This should be not necessary if you called e.g. bring_up.py before. "
    "Default: False"
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(load_calibration=args.load_calibration, host=args.host)
if station.rc.run_local:
    host = get_hostname()
else:
    host = station.remote_host

station.radiant_sig_gen_off()
station.radiant_sig_gen_configure(
    pulse=False, band=args.band
)
if args.load_calibration:
    station.radiant_pedestal_update()

station.radiant_sig_gen_on()
station.radiant_sig_gen_set_frequency(
    frequency=args.frequency
)

station.radiant_pedestal_update()  # this seems to be necessary, otherwise the timing will be all 0's ...
timings = {}

logging.info("Start recording timing ... ")
for quad in range(3):
    channels = get_channels_for_quad(quad)
    t = record_for_quad(station, quad, args.num_recordings)
    for ch in channels:
        logging.info(f"Channel {ch:02d}: {np.mean(t[ch])} ns")
        timings[str(ch)] = t[ch]

station.radiant_sig_gen_off()
station.radiant_calselect(None)
logging.info(" ... finished.")

now = dt.datetime.now(dt.UTC)
timestamp_last_calibration = get_date_of_calibration_file(station)

np.savez(f"{args.data_dir}/timing_{host}_{now.strftime('%Y_%m_%d-%H%M')}.npz", time=now.timestamp(), last_calibration=timestamp_last_calibration, **timings)
