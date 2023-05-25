import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument('-f', '--frequency', type=float, default=400, help='sine wave generator frequency in MHz')
parser.add_argument('--pulse', action='store_true', help='switch signal generator to pulse mode')
parser.add_argument('-q', '--quad', type=int, choices=[0, 1, 2, 3, 4, 5], default=0, help='quad to connect to the signal generator')
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

# Bands are:
# 0 : 50-100 MHz
# 1 : 100-300 MHz
# 2 : 300-600 MHz
# 3 : 600 MHz+
# The pulse path doesn't go through the band filter, so 'band' for it doesn't matter.
band = 0
if args.frequency > 100:
    band = 1
if args.frequency > 300:
    band = 2
if args.frequency > 600:
    band = 3

station.radiant_sig_gen_off()
station.radiant_sig_gen_configure(pulse=args.pulse, band=band)
station.radiant_sig_gen_on()
if not args.pulse:
    station.radiant_sig_gen_set_frequency(frequency=args.frequency)
station.radiant_calselect(quad=args.quad)
