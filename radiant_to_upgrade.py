#!/usr/bin/env python3
import stationrc.bbb
import time
import sys

bootload_id = 0x5244424C
normal_id = 0x52444E54

station = stationrc.bbb.Station(start_thread=False)
dev = station.radiant_board
# reset command path
dev.reset()

print("Booting upgrade image...", end='', flush=True)
dev.reboot(1)
time.sleep(1)
dev.reset()
id = dev.read(dev.map['FPGA_ID'])
if id != normal_id:
    print("Reboot to upgrade failed:", hex(id))
    sys.exit(1)
else:
    print("RADIANT is running upgrade image:")
    dev.identify()
    sys.exit(0)
