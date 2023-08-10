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
args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

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
    ok[ch] = stationrc.remote_control.initial_tune(station, ch)

station.radiant_low_level_interface.calibration_save()
station.radiant_sig_gen_off()
station.radiant_calselect(None)

for ch in ok.keys():
    print(f"ch. {ch:2d} - {'OK' if ok[ch] else 'FAILED'}")
