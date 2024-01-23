import pathlib

import stationrc.common
from .RunConfig import RunConfig


class Run(object):
    def __init__(self, station):
        self.run_conf = RunConfig.load_default_config()
        self.station = station

    def start(self, delete_src=False, rootify=False):
        self.station.set_run_conf(self.run_conf)
        res = self.station.daq_run_start()
        self.station.daq_run_wait()
        self.station.retrieve_data(res["data_dir"], delete_src=delete_src)
        data_dir = (
            pathlib.Path(self.station.station_conf["daq"]["data_directory"])
            / pathlib.Path(res["data_dir"]).parts[-1]
        )
        if rootify:
            stationrc.common.rootify(
                data_dir,
                self.station.station_conf["daq"]["mattak_directory"],
            )
        return data_dir