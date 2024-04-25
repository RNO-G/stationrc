import json
import logging
import pathlib
import os

import stationrc.common
from .RADIANTLowLevelInterface import RADIANTLowLevelInterface
from .RemoteControl import RemoteControl, get_ip


class VirtualStation(object):
    def __init__(self, force_run_mode=None):
        """

        Parameters
        ----------

        force_run_mode: None or str (Default: None)
            Force to run locally or remotely.

                * None: Automatically determine whether radiant is available
                * "local": Force to run locally
                * "remote": Force to run remotely
        """
        self.logger = logging.getLogger("VirtualStation")

        if force_run_mode is None:
            # check if radiant device is available. If yes run locally
            run_local = os.path.exists("/dev/ttyRadiant")
        elif force_run_mode == "local":
            run_local = True
        elif force_run_mode == "remote":
            run_local = False
        else:
            raise ValueError("Invalid value for `force_run_mode`")

        with open(
            pathlib.Path(__file__).parent / "conf/virtual_station_conf.json", "r"
        ) as f:
            self.station_conf = json.load(f)

        self.rc = RemoteControl(
            self.station_conf["remote_control"]["host"],
            self.station_conf["remote_control"]["port"],
            self.station_conf["remote_control"]["logger_port"],
            run_local=run_local
        )
        self.radiant_low_level_interface = RADIANTLowLevelInterface(
            remote_control=self.rc
        )

    def daq_record_data(
        self,
        num_events=1,
        trigger_channels=[],
        trigger_threshold=1.05,
        trigger_coincidence=1,
        force_trigger=False,
        force_trigger_interval=1,
        use_uart=False,
        read_header=False,
        read_pedestal=False,
    ):
        return self.rc.send_command(
            "station",
            "daq_record_data",
            {
                "num_events": num_events,
                "trigger_channels": trigger_channels,
                "trigger_threshold": trigger_threshold,
                "trigger_coincidence": trigger_coincidence,
                "force_trigger": force_trigger,
                "force_trigger_interval": force_trigger_interval,
                "use_uart": use_uart,
                "read_header": read_header,
                "read_pedestal": read_pedestal,
            },
        )

    def reset_radiant_board(self):
        return self.rc.send_command("station", "reset_radiant_board")

    def daq_run_start(self):
        return self.rc.send_command("station", "daq_run_start")

    def daq_run_terminate(self):
        self.rc.send_command("station", "daq_run_terminate")

    def daq_run_wait(self):
        self.rc.send_command("station", "daq_run_wait")

    def get_controller_board_monitoring(self):
        data = self.rc.send_command("controller-board", "#MONITOR")
        res = json.loads(data)
        return res

    def get_radiant_board_dna(self):
        return self.radiant_low_level_interface.dna()

    def get_radiant_board_id(self):
        return self.rc.send_command("radiant-board", "identify")

    def get_radiant_board_mcu_uid(self):
        return self.radiant_low_level_interface.board_manager_uid()

    def radiant_calselect(self, quad):
        return self.rc.send_command("radiant-board", "calSelect", {"quad": quad})

    def radiant_pedestal_get(self):
        return self.rc.send_command("radiant-calib", "getPedestals", {"asList": True})

    def radiant_pedestal_set(self, value):
        PEDESTAL_VALUE_MIN = 0
        PEDESTAL_VALUE_MAX = 3000  # Corresponds to a DC offset of 3000 / 4096 * 3.3V = 2.42V (max. input voltage for the LAB4D is 2.5V)
        if value < PEDESTAL_VALUE_MIN or value > PEDESTAL_VALUE_MAX:
            err = (f"Only accepting pedestals of {PEDESTAL_VALUE_MIN} <= value <= "
                   f"{PEDESTAL_VALUE_MAX}. Doing nothing.")
            self.logger.error(err)
            raise ValueError(err)

        self.rc.send_command("radiant-board", "pedestal", {"val": value})
        self.radiant_pedestal_update()

    def radiant_pedestal_update(self):
        self.rc.send_command("radiant-calib", "updatePedestals")

    def radiant_revision(self):
        return self.radiant_low_level_interface.read_register(
            self.radiant_low_level_interface.BOARD_MANAGER_BASE_ADDRESS + 0x5C
        )

    def radiant_sample_rate(self):
        return self.radiant_low_level_interface.read_register(
            self.radiant_low_level_interface.BOARD_MANAGER_BASE_ADDRESS + 0xF0
        )

    def radiant_setup(self, version=3):
        return self.rc.send_command("station", "radiant_setup", {"version": version})

    def radiant_sig_gen_configure(self, pulse=False, band=0):
        self.rc.send_command(
            "radiant-sig-gen", "signal", {"pulse": pulse, "band": band}
        )

    def radiant_sig_gen_off(self):
        self.rc.send_command("radiant-sig-gen", "enable", {"onoff": False})

    def radiant_sig_gen_on(self):
        self.rc.send_command("radiant-sig-gen", "enable", {"onoff": True})

    def radiant_sig_gen_select_band(self, frequency):
        band = 0
        if frequency > 100:
            band = 1
        if frequency > 300:
            band = 2
        if frequency > 600:
            band = 3
        self.radiant_sig_gen_configure(pulse=False, band=band)

    def radiant_sig_gen_set_frequency(self, frequency):
        self.rc.send_command("radiant-sig-gen", "setFrequency", {"freq": frequency})

    def retrieve_data(self, src, delete_src=False):
        cmd = ["rsync", "--archive", "--compress", "--verbose", "--stats"]
        if delete_src:
            cmd.append("--remove-source-files")

        self.proc = stationrc.common.Executor(
            cmd=cmd
            + [
                f'{self.station_conf["remote_control"]["user"]}@{self.station_conf["remote_control"]["host"]}:{src}',
                self.station_conf["daq"]["data_directory"],
            ],
            logger=self.logger,
        )
        self.proc.wait()

    def set_run_conf(self, conf):
        self.rc.send_command("station", "write_run_conf", {"data": conf.conf})

    def surface_amps_power_off(self):
        self.rc.send_command("controller-board", "#AMPS-SET 0 0")

    def surface_amps_power_on(self):
        self.rc.send_command("controller-board", "#AMPS-SET 22 0")

    def set_remote_logger_handler(self):
        self.logger.info("Set remote logger handler for station")
        return self.send_command("station", "add_logger_handler",
                                 {"host": get_ip(), "port": self._logger_port})