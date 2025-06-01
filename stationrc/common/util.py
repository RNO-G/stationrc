import sys
import os
import json
import numpy as np
import logging
import logging.config
import pathlib

from stationrc.common.Executor import Executor
from stationrc.common.RNOGDataFile import RNOGDataFile

# Trigger type encoding in header files
trigger_names = {
    1: "SOFT",
    2: "EXT",
    4: "RF_LT_SIMPLE",
    8: "RF_LT_PHASED",
    64: "RADIANTX",
    80: "RADIANT0",
    96: "RADIANT1",
    128: "PPS"
}

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
    """ Dumps data from binary RNO-G DAQ files into a dictionary.

    Parameters
    ----------
    wfs_file : str
        Path to the waveform file to read (typical syntax `XXXXXX.wf.dat.gz`)
    read_header : bool, optional
        If True, read the header file (default: False)
    hdr_file : str, optional
        Path to the header file to read (typical syntax `XXXXXX.hd.dat.gz`), required if `read_header` is True
    read_pedestal : bool, optional
        If True, read the pedestal file (default: False)
    ped_file : str, optional
        Path to the pedestal file to read (typical syntax `pedestals.dat.gz`), required if `read_pedestal` is True

    Returns
    -------
    data : dict
        Dictionary containing the data from the files. The keys are "WAVEFORM", "HEADER" and "PEDESTAL"
        and the values are lists of dictionaries containing the data from each packet.
    """

    if read_header and hdr_file is None:
        raise ValueError("You have to specify 'hdr_file'!")

    if read_pedestal and ped_file is None:
        raise ValueError("You have to specify 'ped_file'!")

    data = {}
    data.update(read_rnog_binary_file(wfs_file, "WAVEFORM"))

    if read_header:
        data.update(read_rnog_binary_file(hdr_file, "HEADER"))

    if read_pedestal:
        data.update(read_rnog_binary_file(ped_file, "PEDESTAL"))

    return data


def read_run_binary(run_dir):
    """ Reads the binary files from a RNO-G run directory """

    if not os.path.isdir(run_dir):
        raise ValueError(f"The (run) directory {run_dir} does not exist!")

    waveforms_dir = os.path.join(run_dir, "waveforms")
    if not os.path.exists(waveforms_dir):
        raise ValueError(f"Waveforms directory {waveforms_dir} does not exist!")

    waveform_files = os.listdir(waveforms_dir)
    if len(waveform_files) == 0:
        raise ValueError(f"Waveforms directory {waveforms_dir} is empty!")

    print(f"Found {len(waveform_files)} waveform files in {waveforms_dir}.")
    waveform_files = sorted(waveform_files)

    headers_dir = os.path.join(run_dir, "header")

    for idx, wf_file in enumerate(waveform_files):
        wf_file_path = os.path.join(waveforms_dir, wf_file)
        hdr_file_path = os.path.join(headers_dir, wf_file.replace("wf", "hd"))

        data = dump_binary(
            wf_file_path,
            read_header=os.path.exists(hdr_file_path),
            hdr_file=hdr_file_path
        )

        if "HEADER" in data:
            hdr_data = data["HEADER"]

        for event_idx, event_wf_data in enumerate(data["WAVEFORM"]):
            event_number = event_wf_data["event_number"]
            run_number = event_wf_data["run_number"]
            station = event_wf_data["station"]
            radiant_sampling_rate = event_wf_data["radiant_sampling_rate"]
            wfs = event_wf_data["radiant_waveforms"]

            if "HEADER" in data:
                header = hdr_data[event_idx]
                assert header["event_number"] == event_number, "Missmatch between wf and hdr data"
                trigger_type = header["trigger_type"]
                trigger_name = trigger_names.get(trigger_type, "UNKNOWN")

            # do something with the data


def setup_logging():
    with open(pathlib.Path(__file__).parent / "conf" / "logging_conf.json", "r") as f:
        conf = json.load(f)
    logging.config.dictConfig(conf)


def read_rnog_binary_file(path, file_type):
    """ Read a RNO-G binary file and return the data as a dictionary.

    This function reads a RNO-G binary file and returns the data as a
    dictionary. All numpy arrays in the data are converted to lists
    (to make it JSON serializable).

    Parameters
    ----------
    path : str
        Path to the RNO-G binary file.
    file_type : str
        Type of the file to read. Can be "WAVEFORM", "HEADER", "PEDESTAL" or "DAQSTATUS".

    Returns
    -------
    data : dict
        Dictionary containing the data from the file. The keys are `file_type`
        and the values are lists of dictionaries containing the data from each packet.

    Example
    -------

    ... code-block:: python

        data = read_rnog_binary_file("path/to/file", "WAVEFORM")
        for event_data in data["WAVEFORM"]:
            print(event_data["event_number"], event_data["radiant_waveforms"])

    """
    f = RNOGDataFile(path)
    data = {file_type: list()}
    while True:
            packet = f.get_next_packet()
            if packet is None:
                break

            for ele in packet:
                if  isinstance(packet[ele], np.ndarray):
                    packet[ele] = packet[ele].tolist()

            data[file_type].append(packet)

    return data

def read_daqstatus(path):
    data = read_rnog_binary_file(path, "DAQSTATUS")
    return data

def read_header(path):
    data = read_rnog_binary_file(path, "HEADER")
    return data


if __name__ == "__main__":

    f = RNOGDataFile(sys.argv[1])

    while True:
        packet = f.get_next_packet()
        if packet is None:
            break

    print("done")