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
    "--max_iterations",
    type=int,
    default=50,
    help="Maximum number of iterations in each tuning step. Default: 50",
)


parser.add_argument(
    "-e",
    "--external",
    action="store_true",
    help="Use external signal",
)

parser.add_argument(
    "--tune-mean",
    dest="tune_with_mean",
    action="store_true",
    help="Skip tuning loop which usese the mean of samples as seam proxy.",
)

parser.add_argument(
    "-q",
    "--quad",
    "--quads",
    dest="quads",
    type=int,
    nargs="+",
    choices=[q for q in range(3)],
    default=[q for q in range(3)],
    help="Quads for tuning"
)

parser.add_argument(
    "-a",
    "--average",
    action="store_true"
)

parser.add_argument(
    "--exclude_channels",
    type=int,
    nargs="+",
    default=[]
)

parser.add_argument(
    "--host",
    type=str,
    default=None,
    help="Specify ip address of host. If `None`, use ip from `virtual_station_config.json`."
)

args = parser.parse_args()

stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation(load_calibration=True, host=args.host)

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

for quad in args.quads:
    chs, tuned = stationrc.remote_control.initial_tune(
        station, quad, args.frequency, max_tries=args.max_iterations, external_signal=args.external,
        tune_with_rolling_mean=args.average, tune_with_mean=args.tune_with_mean, exclude_channels=args.exclude_channels,
        selected_channels=args.channel)
    for ch, t in zip(chs, tuned):
        ok[ch] = t

station.radiant_low_level_interface.calibration_save()
station.radiant_sig_gen_off()
station.radiant_calselect(None)

for ch in ok:
    if ch in args.channel and ch not in args.exclude_channels:
        print(f"ch. {ch:2d} - {'OK' if ok[ch] else 'FAILED'}")
