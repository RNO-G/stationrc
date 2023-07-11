import json
import logging
import pathlib
import zmq

import stationrc.common


class VirtualStation(object):
    def __init__(self):
        self.logger = logging.getLogger("VirtualStation")

        with open(
            pathlib.Path(__file__).parent / "conf/virtual_station_conf.json", "r"
        ) as f:
            self.station_conf = json.load(f)

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        socket = f'tcp://{self.station_conf["remote_control"]["host"]}:{self.station_conf["remote_control"]["port"]}'
        self.logger.debug(f'Connect to socket: "{socket}".')
        self.socket.connect(socket)

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
        return self._send_command(
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

    def daq_run_start(self):
        return self._send_command("station", "daq_run_start")

    def daq_run_terminate(self):
        self._send_command("station", "daq_run_terminate")

    def daq_run_wait(self):
        self._send_command("station", "daq_run_wait")

    def get_controller_board_monitoring(self):
        # TODO: parse all fields in data

        data = self._send_command("controller-board", "#MONITOR")
        res = {"analog": {}, "power": {}, "temp": {}}
        tokens = data.split()
        res["analog"]["timestamp"] = int(tokens[4][:-1])
        res["power"]["timestamp"] = int(tokens[26][:-1])
        res["temp"]["timestamp"] = int(tokens[43][:-1])
        return res

    def get_radiant_board_dna(self):
        return int(self._send_command("radiant-board", "dna"))

    def get_radiant_board_id(self):
        return self._send_command("radiant-board", "identify")

    def radiant_calselect(self, quad):
        return self._send_command("radiant-board", "calSelect", {"quad": quad})

    def radiant_read_register(self, name):
        return self._send_command("radiant-board", "readReg", {"name": name})

    def radiant_setup(self):
        return self._send_command("station", "radiant_setup")

    def radiant_sig_gen_configure(self, pulse=False, band=0):
        self._send_command("radiant-sig-gen", "signal", {"pulse": pulse, "band": band})

    def radiant_sig_gen_off(self):
        self._send_command("radiant-sig-gen", "enable", {"onoff": False})

    def radiant_sig_gen_on(self):
        self._send_command("radiant-sig-gen", "enable", {"onoff": True})

    def radiant_sig_gen_set_frequency(self, frequency):
        self._send_command("radiant-sig-gen", "setFrequency", {"freq": frequency})

    def radiant_tune_initial(self, reset=False, mask=0xFFFFFF):
        return self._send_command(
            "station", "radiant_tune_initial", {"reset": reset, "mask": mask}
        )

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
        self._send_command("station", "write_run_conf", {"data": conf.conf})

    def surface_amps_power_off(self):
        self._send_command("controller-board", "#AMPS-SET 0 0")

    def surface_amps_power_on(self):
        self._send_command("controller-board", "#AMPS-SET 22 0")

    def _send_command(self, device, cmd, data=None):
        tx = {"device": device, "cmd": cmd}
        if data != None:
            tx["data"] = json.dumps(data)
        self.logger.debug(f'Sending command: "{tx}".')
        self.socket.send_json(tx)
        message = self.socket.recv_json()
        self.logger.debug(f'Received reply: "{message}"')
        if not "status" in message or message["status"] != "OK":
            self.logger.error(f'Sent: "{tx}". Received: "{message}"')
            return None
        if not "data" in message:
            return None
        return message["data"]
