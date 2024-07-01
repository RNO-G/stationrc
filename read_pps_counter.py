
import stationrc.common
import stationrc.remote_control
import argparse
import time

parser = argparse.ArgumentParser()

parser.add_argument(
    "--host", "--hosts",
    dest="hosts",
    type=str, default=[None],
    nargs="+",
    help="Specify ip address of host. If `None`, use ip from config in stationrc.")

args = parser.parse_args()

stationrc.common.setup_logging()

for host in args.hosts:
    station = stationrc.remote_control.VirtualStation(host=host)
    print("Read ppc counter for 10 seconds ...")

    for _ in range(10):
        station.radiant_low_level_interface.read_register(0x30004)
        time.sleep(1)