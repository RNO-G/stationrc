import sys
import os
import argparse

import stationrc.common


def read_raw_run(path_to_run_dir):
    """ Read raw data from a run directory.

    Example of how to access run data.

    Parameters
    ----------
    path_to_run_dir : str
        Path to the run directory containing the raw data files.
    """

    if not os.path.isdir(path_to_run_dir):
        raise ValueError(f"The (run) directory {path_to_run_dir} does not exist!")

    waveforms_dir = os.path.join(path_to_run_dir, "waveforms")
    if not os.path.exists(waveforms_dir):
        raise ValueError(f"Waveforms directory {waveforms_dir} does not exist!")

    waveform_files = os.listdir(waveforms_dir)
    if len(waveform_files) == 0:
        raise ValueError(f"Waveforms directory {waveforms_dir} is empty!")

    print(f"Found {len(waveform_files)} waveform files in {waveforms_dir}.")
    waveform_files = sorted(waveform_files)

    headers_dir = os.path.join(path_to_run_dir, "header")

    for idx, wf_file in enumerate(waveform_files):
        wf_file_path = os.path.join(waveforms_dir, wf_file)
        hdr_file_path = os.path.join(headers_dir, wf_file.replace("wf", "hd"))

        data = stationrc.common.dump_binary(
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

            # do something with the data


parser = argparse.ArgumentParser()
parser.add_argument("filename", help="RNO-G data file")
args = parser.parse_args()

if os.path.isdir(args.filename):
    read_raw_run(args.filename)
else:
    # Example of how to access read a single binary RNO-G data file
    data = stationrc.common.RNOGDataFile(args.filename)
    while True:
        packet = data.get_next_packet()
        if packet == None:
            break
        print(packet)
