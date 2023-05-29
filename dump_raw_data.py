import argparse

import stationrc.common


parser = argparse.ArgumentParser()
parser.add_argument("filename", help="RNO-G data file")
args = parser.parse_args()

data = stationrc.common.RNOGDataFile(args.filename)
while True:
    packet = data.get_next_packet()
    if packet == None:
        break
    print(packet)
