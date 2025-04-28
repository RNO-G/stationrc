import json
import logging
import logging.config
import pathlib
import numpy as np

from stationrc.common.Executor import Executor
from stationrc.common.RNOGDataFile import RNOGDataFile


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

    data = {}
    data.update(read_rnog_binary_file(wfs_file, "WAVEFORM"))

    if read_header:
        data.update(read_rnog_binary_file(hdr_file, "HEADER"))

    if read_pedestal:
        data.update(read_rnog_binary_file(ped_file, "PEDESTAL"))

    return data


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
