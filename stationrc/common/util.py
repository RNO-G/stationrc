import json
import logging
import logging.config
import pathlib

from .Executor import Executor
from .RNOGDataFile import RNOGDataFile

def rootify(data_dir, mattak_dir="", logger=logging.getLogger("root")):
    datadir = pathlib.Path(data_dir)

    daqstatus_root = datadir / "daqstatus.root"
    header_root = datadir / "header.root"
    waveforms_root = datadir / "waveforms.root"

    daq_files = list((datadir / "daqstatus").glob("*.ds.dat*"))
    daq_files.sort()
    proc = Executor(
        cmd=[pathlib.Path(mattak_dir) / "rno-g-convert", "ds", daqstatus_root] + daq_files,
        logger=logger,
    )
    proc.wait()


    hdr_files = list((datadir / "header").glob("*.hd.dat*"))
    hdr_files.sort()
    proc = Executor(
        cmd=[pathlib.Path(mattak_dir) / "rno-g-convert", "hd", header_root] + hdr_files,
        logger=logger,
    )
    proc.wait()


    wfs_files = list((datadir / "waveforms").glob("*.wf.dat*"))
    wfs_files.sort()
    proc = Executor(
        cmd=[pathlib.Path(mattak_dir) / "rno-g-convert", "wf", waveforms_root] + wfs_files,
        logger=logger,
    )
    proc.wait()
    proc = Executor(
        cmd=[
            pathlib.Path(mattak_dir) / "rno-g-combine",
            datadir / "combined.root",
            waveforms_root,
            header_root,
            daqstatus_root,
        ],
        logger=logger,
    )
    proc.wait()


def dump_binary(wfs_file, read_header=False, hdr_file=None, read_pedestal=False, ped_file=None):

    if read_header and hdr_file is None:
        raise ValueError("You have to specify 'hdr_file'!")

    if read_pedestal and ped_file is None:
        raise ValueError("You have to specify 'ped_file'!")

    waveforms = RNOGDataFile(wfs_file)

    data = {"WAVEFORM": []}
    while True:
        packet = waveforms.get_next_packet()
        if packet is None:
            break

        packet["radiant_waveforms"] = packet["radiant_waveforms"].tolist()
        packet["lt_waveforms"] = packet["lt_waveforms"].tolist()
        packet["digitizer_readout_delay"] = packet["digitizer_readout_delay"].tolist()
        data["WAVEFORM"].append(packet)

    if read_header:
        headers = RNOGDataFile(hdr_file)

        data["HEADER"] = list()
        while True:
            packet = headers.get_next_packet()
            if packet is None:
                break

            packet["radiant_start_windows"] = packet[
                "radiant_start_windows"
            ].tolist()
            packet["simple_trig_conf"]["_bitfield_stuff"] = packet[
                "simple_trig_conf"
            ]["_bitfield_stuff"].tolist()
            packet["trig_conf"]["_bitfield_stuff"] = packet["trig_conf"][
                "_bitfield_stuff"
            ].tolist()

            data["HEADER"].append(packet)

    if read_pedestal:
        pedestals = RNOGDataFile(ped_file)

        data["PEDESTAL"] = list()
        while True:
            packet = pedestals.get_next_packet()
            if packet is None:
                break

            packet["vbias"] = packet["vbias"].tolist()
            packet["pedestals"] = packet["pedestals"].tolist()

            data["PEDESTAL"].append(packet)

    return data


def setup_logging():
    with open(pathlib.Path(__file__).parent / "conf" / "logging_conf.json", "r") as f:
        conf = json.load(f)
    logging.config.dictConfig(conf)
