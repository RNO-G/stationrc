import argparse
import matplotlib.pyplot as plt

import stationrc.common


def plot_pedestals(packet):
    fig = plt.figure()
    ax = fig.subplots()
    for ch, wvf in enumerate(packet["pedestals"]):
        ax.plot(wvf, label=f"ch. {ch}")
    ax.legend()


def plot_waveform(packet):
    fig = plt.figure()
    ax = fig.subplots()
    for ch, wvf in enumerate(packet["radiant_waveforms"]):
        ax.plot(wvf, label=f"ch. {ch}")
    ax.legend()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="RNO-G data file")
    args = parser.parse_args()

    data = stationrc.common.RNOGDataFile(args.filename)
    while True:
        packet = data.get_next_packet()
        if packet == None:
            break
        if packet["type"] == "PEDESTAL":
            plot_pedestals(packet)
        elif packet["type"] == "WAVEFORM":
            plot_waveform(packet)
    plt.show()
