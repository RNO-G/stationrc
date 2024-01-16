import json
import libconf
import logging
import pathlib
import threading
import zmq

from cobs.cobs import DecodeError

import stationrc.common
import stationrc.radiant
from .ControllerBoard import ControllerBoard


class Station(object):
    def __init__(self):
        self.logger = logging.getLogger("Station")

        with open(
            pathlib.Path(__file__).parent / "conf" / "station_conf.json", "r"
        ) as f:
            self.station_conf = json.load(f)

        self.controller_board = ControllerBoard(
            uart_device=self.station_conf["daq"]["controller_board_dev"],
            uart_baudrate=self.station_conf["daq"]["controller_board_baudrate"],
        )

        # radiant_board is implemented as property and with set _radiant_board the first time its called.
        self._radiant_board = None

        self.thr_rc = threading.Thread(
            target=Station._receive_remote_command, args=[self]
        )
        self.thr_rc.start()

    @property
    def radiant_board(self):
        if self._radiant_board is None:
            from stationrc.radiant.radiant import RADIANT
            self._radiant_board = RADIANT(port=self.station_conf["daq"]["radiant_board_dev"])

        return self._radiant_board

    def reset_radiant_board(self):
        self._radiant_board = None

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
        if num_events <= 0:
            self.logger.error("Infinite recording not supported.")
            return
        mask = 0
        for ch in trigger_channels:
            mask |= 1 << ch
        cmd = [
            self.station_conf["daq"]["radiant-try-event_executable"],
            "-N",
            f"{num_events}",
            "-M",
            f"{mask}",
            "-T",
            f"{trigger_threshold}",
            "-C",
            f"{trigger_coincidence}",
        ]
        if force_trigger:
            cmd += ["-f", "-I", f"{force_trigger_interval}"]

        if use_uart:
            cmd += ["-u"]

        self.acq_proc = stationrc.common.Executor(
            cmd=cmd,
            logger=self.logger,
        )
        self.acq_proc.wait()

        data = {"WAVEFORM": []}
        waveforms = stationrc.common.RNOGDataFile(
            self.station_conf["daq"]["radiant-try-event_wfs_file"]
        )

        while True:
            packet = waveforms.get_next_packet()
            if packet == None:
                break
            packet["radiant_waveforms"] = packet["radiant_waveforms"].tolist()
            packet["lt_waveforms"] = packet["lt_waveforms"].tolist()
            data["WAVEFORM"].append(packet)

        if read_header:
            headers = stationrc.common.RNOGDataFile(
                self.station_conf["daq"]["radiant-try-event_hdr_file"]
            )

            data["HEADER"] = []

            while True:
                packet = headers.get_next_packet()
                if packet == None:
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
            pedestals = stationrc.common.RNOGDataFile(
                self.station_conf["daq"]["radiant-try-event_ped_file"]
            )

            data["PEDESTAL"] = list()

            while True:
                packet = pedestals.get_next_packet()
                if packet == None:
                    break

                packet["vbias"] = packet["vbias"].tolist()
                packet["pedestals"] = packet["pedestals"].tolist()

                data["PEDESTAL"].append(packet)

        return {"data": data}

    def daq_run_start(self):
        data_dir = self.get_data_dir()
        self.acq_proc = stationrc.common.Executor(
            cmd=self.station_conf["daq"]["rno-g-acq_executable"], logger=self.logger
        )

        return {"data_dir": str(data_dir)}

    def daq_run_terminate(self):
        self.acq_proc.terminate()

    def daq_run_wait(self):
        self.acq_proc.wait()

    def get_data_dir(self):
        with open(self.station_conf["daq"]["run_conf"], "r") as f:
            conf = libconf.load(f)
        with open(conf["output"]["runfile"], "r") as f:
            runnumber = int(f.readline())
        return pathlib.Path(conf["output"]["base_dir"]) / f"run{runnumber}"

    def radiant_calib_isels(self, niter=10, buff=32, step=4, voltage_setting=1250):
        stationrc.radiant.calib_isels(
            self.radiant_board,
            niter=niter,
            buff=buff,
            step=step,
            voltage_setting=voltage_setting,
        )

    def radiant_setup(self, version=3):
        stationrc.radiant.setup_radiant(self, version)

    def radiant_tune_initial(self, reset=False, mask=0xFFFFFF):
        fail_mask = stationrc.radiant.tune_initial(
            self.radiant_board, do_reset=reset, mask=mask
        )
        return {"fail_mask": fail_mask}

    def write_run_conf(self, data):
        with open(self.station_conf["daq"]["run_conf"], "w") as f:
            libconf.dump(data, f)

    def _receive_remote_command(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f'tcp://*:{self.station_conf["remote_control"]["port"]}')

        while True:
            message = socket.recv_json()
            self.logger.debug(f'Received remote command: "{message}".')
            if not ("device" in message and "cmd" in message):
                self.logger.error(f'Received malformed command: "{message}".')
                socket.send_json({"status": "ERROR"})

            elif message["device"] == "controller-board":
                res = self.controller_board.run_command(message["cmd"])
                socket.send_json({"status": "OK", "data": res})

            elif message["device"] in [
                "radiant-board",
                "radiant-calib",
                "radiant-calram",
                "radiant-dma",
                "radiant-labc",
                "radiant-sig-gen",
                "station",
            ]:
                if message["device"] == "radiant-board":
                    dev = self.radiant_board
                elif message["device"] == "radiant-calib":
                    dev = self.radiant_board.calib
                elif message["device"] == "radiant-calram":
                    dev = self.radiant_board.calram
                elif message["device"] == "radiant-dma":
                    dev = self.radiant_board.dma
                elif message["device"] == "radiant-labc":
                    dev = self.radiant_board.labc
                elif message["device"] == "radiant-sig-gen":
                    dev = self.radiant_board.radsig
                elif message["device"] == "station":
                    dev = self

                if hasattr(dev, message["cmd"]):
                    func = getattr(dev, message["cmd"])
                    try:
                        if "data" in message:
                            data = json.loads(message["data"])
                            res = func(**data)
                        else:
                            res = func()

                        if res != None:
                            socket.send_json({"status": "OK", "data": res})
                        else:
                            socket.send_json({"status": "OK"})

                    except DecodeError:
                        socket.send_json({"status": "ERROR", "data": "Catched a cobs.DecodeError"})

                else:
                    socket.send_json({"status": "UNKNOWN_CMD"})

            else:
                socket.send_json({"status": "UNKNOWN_DEV"})
