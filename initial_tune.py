import argparse

import stationrc.common
import stationrc.remote_control


parser = argparse.ArgumentParser()
parser.add_argument(
    "-c",
    "--channel",
    type=int,
    nargs="+",
    choices=[ch for ch in range(24)],
    default=[ch for ch in range(24)],
    help="channels for tuning",
)
parser.add_argument("--reset", action="store_true", help="reset LAB4Ds")
parser.add_argument("--reset_radiant", action="store_true", help="Reset Radiant")

parser.add_argument(
    "-f",
    "--frequency",
    type=float,
    default=510,
    help="Specify tuning frequency. The band is choosen automatically. Default: 510 MHz",
)

parser.add_argument(
    "-e",
    "--external",
    action="store_true",
    help="Use external signal",
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

if args.reset_radiant:
    station.reset_radiant_board()

if args.reset:
    for ch in args.channel:
        station.radiant_low_level_interface.calibration_specifics_reset(ch)
        station.radiant_low_level_interface.lab4d_controller_default(ch)
    for ch in args.channel:
        station.radiant_low_level_interface.lab4d_controller_automatch_phab(ch)
else:
    station.radiant_low_level_interface.calibration_load()



ok = dict()
for ch in args.channel:
    ok[ch] = stationrc.remote_control.initial_tune(station, ch, args.frequency, external_signal=args.external)

station.radiant_low_level_interface.calibration_save()
station.radiant_sig_gen_off()
station.radiant_calselect(None)

for ch in ok.keys():
    print(f"ch. {ch:2d} - {'OK' if ok[ch] else 'FAILED'}")
