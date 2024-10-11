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
    def __init__(self, start_thread=True, poll_timeout_ms=1000):
        self.logger = logging.getLogger("Station")
        self.poll_timeout_ms = poll_timeout_ms

        with open(
            pathlib.Path(__file__).parent / "conf" / "station_conf.json", "r"
        ) as f:
            self.station_conf = json.load(f)

        # radiant_board is implemented as property and with set _radiant_board the first time its called.
        self._radiant_board = None

        if start_thread:
            self.do_run = True
            self.controller_board = ControllerBoard(uart_device=self.station_conf["daq"]["controller_board_dev"])

            self.thr_rc = threading.Thread(
                target=Station._receive_remote_command, args=[self])

            self.thr_rc.start()

            self.radiant_board.calib.load(self._radiant_board.uid())

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
        self.logger.info("Start recording data (radiant-try-event) ...")

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

        self.logger.info("... finished.")
        data = stationrc.common.dump_binary(
            wfs_file=self.station_conf["daq"]["radiant-try-event_wfs_file"],
            read_header=read_header,
            hdr_file=self.station_conf["daq"]["radiant-try-event_hdr_file"],
            read_pedestal=read_pedestal,
            ped_file=self.station_conf["daq"]["radiant-try-event_ped_file"]
        )

        return {"data": data}

    def daq_run_start(self):
        self.logger.info("Start daq run ...")
        data_dir = self.get_data_dir()
        self.acq_proc = stationrc.common.Executor(
            cmd=[self.station_conf["daq"]["rno-g-acq_executable"],
                 self.station_conf["daq"]["run_conf"]],
            logger=self.logger
        )

        return {"data_dir": str(data_dir)}

    def daq_run_terminate(self):
        self.acq_proc.terminate()
        self.logger.info("... finished daq run.")

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

    def shut_down(self):
        self.logger.warning("Shutting down!")
        self.controller_board.shut_down()
        self.do_run = False
        self.thr_rc.join()

    def write_run_conf(self, data):
        with open(self.station_conf["daq"]["run_conf"], "w") as f:
            libconf.dump(data, f)

    def parse_message_execute_command(self, message):
        self.logger.debug(f'Received remote command: "{message}".')
        if not ("device" in message and "cmd" in message):
            self.logger.error(f'Received malformed command: "{message}".')
            return "ERROR", None

        elif message["device"] == "controller-board":
            res = self.controller_board.run_command(message["cmd"])
            return "OK", res

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
                if "data" in message:
                    data = json.loads(message["data"])
                    res = func(**data)
                else:
                    res = func()

                return "OK", res

            else:
                return "UNKNOWN_CMD", None

        else:
            return "UNKNOWN_DEV", None

    def _receive_remote_command(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f'tcp://*:{self.station_conf["remote_control"]["port"]}')
        poller = zmq.Poller()
        poller.register(socket, zmq.POLLIN)

        while self.do_run:
            events = poller.poll(self.poll_timeout_ms)
            for ev in events:
                if ev[1] == zmq.POLLIN:
                    message = ev[0].recv_json()
                    try:
                        status, data = self.parse_message_execute_command(message)
                        if data is not None:
                            socket.send_json({"status": status, "data": data})
                        else:
                            socket.send_json({"status": status})

                    except DecodeError:
                        self.logger.warning("Detect cobs.DecodeError! Reinitialize radiant object ...")
                        self._radiant_board = None
                        try:
                            status, data = self.parse_message_execute_command(message)
                            if data is not None:
                                socket.send_json({"status": status, "data": data})
                            else:
                                socket.send_json({"status": status})

                        except DecodeError:
                            socket.send_json({"status": "ERROR", "data": "Catched a cobs.DecodeError"})
