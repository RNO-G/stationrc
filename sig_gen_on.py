import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument(
    "-f",
    "--frequency",
    type=float,
    default=400,
    help="sine wave generator frequency in MHz",
)
parser.add_argument(
    "-q",
    "--quad",
    type=int,
    choices=[0, 1, 2],
    default=0,
    help="quad to connect to the signal generator",
)
parser.add_argument(
    "-b",
    "--band",
    type=int,
    choices=[0, 1, 2, 3],
    default=None,
    help="Select filter band. 0: 5-100 MHz, 1: 100-300 MHz, 2: 300-600 MHz, 3: 600+ MHz. If None (default) select band based on given frequency",
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

station.radiant_sig_gen_off()
if args.band is None:
    station.radiant_sig_gen_select_band(frequency=args.frequency)
else:
    station.radiant_sig_gen_configure(pulse=args.pulse, band=args.band)
station.radiant_sig_gen_on()
station.radiant_sig_gen_set_frequency(frequency=args.frequency)
station.radiant_calselect(quad=args.quad)
