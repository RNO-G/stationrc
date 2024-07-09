import pathlib

import stationrc.common
from stationrc.remote_control import utils
from .RunConfig import RunConfig


def get_host_from_ip(ip):
    for key, value in utils.host_aliases.items():
        if ip == value:
            return key

    return ip


class Run(object):
    def __init__(self, station, config_file=None):
        if config_file is None:
            self.run_conf = RunConfig.load_default_config()
        else:
            self.run_conf = RunConfig.load_config(config_file)

        self.station = station

    def start(self, delete_src=False, rootify=False):
        self.station.set_run_conf(self.run_conf)
        res = self.station.daq_run_start()
        self.station.daq_run_wait()

        host = get_host_from_ip(self.station.remote_host)
        data_dir = (
            pathlib.Path(self.station.station_conf["daq"]["data_directory"])
            / pathlib.Path(host)
            / pathlib.Path(res["data_dir"]).parts[-1]
        )

        if not data_dir.exists():
            print(f"{data_dir} does not exist. Create it ...")
            data_dir.mkdir(parents=True)

        self.station.retrieve_data(res["data_dir"], target_dir=data_dir, delete_src=delete_src)

        if rootify:
            stationrc.common.rootify(
                data_dir,
                self.station.station_conf["daq"]["mattak_directory"],
            )

        return data_dir