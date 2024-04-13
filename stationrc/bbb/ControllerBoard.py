import logging
import serial
import subprocess
import threading
import time


class ControllerBoard(object):
    def __init__(
        self, uart_device, uart_baudrate=115200, uart_timeout=0.25, background_sleep=5
    ):
        self.logger = logging.getLogger("ControllerBoard")

        self.background_sleep = background_sleep
        self.do_run = True
        self.lock = threading.RLock()
        self.uart = serial.Serial(
            port=uart_device, baudrate=uart_baudrate, timeout=uart_timeout
        )  # TODO: optimize timeout for commands to return a result

        self.thr_bkg = threading.Thread(
            target=ControllerBoard.receive_background_data, args=[self]
        )
        self.thr_bkg.start()

    def drain_buffer(self):
        with self.lock:
            while True:
                data = self._readline()
                if data == None:
                    break
                self.logger.debug(f"Drained {data} from buffer.")

    def receive_background_data(self):
        self.drain_buffer()
        while self.do_run:
            time.sleep(self.background_sleep)
            with self.lock:
                while True:
                    data = self._readline()
                    if data == None:
                        break
                    self.logger.info(data)

    def run_command(self, cmd):
        self.drain_buffer()
        cmd = cmd.upper()  # all command are uppercase
        if cmd[0] != "#":  # all commands start with '#'
            cmd = "#" + cmd
        self.logger.debug(f'Sending "{cmd}" to UART')
        result = ""
        with self.lock:
            self._write(cmd)
            while True:
                data = self._readline()
                if data == None:
                    break
                self.logger.info(data)
                if result != "":
                    result += "\n"
                result += data
        return result

    def shut_down(self):
        self.logger.warning("Shutting down!")
        self.do_run = False
        self.thr_bkg.join()
        self.uart.close()
        subprocess.run(["stty", "-F", self.uart.name, "sane"])
        subprocess.run(
            ["stty", "-F", self.uart.name, "115200", "-echo", "igncr", "-inlcr"]
        )

    def _readline(self):
        data = self.uart.read_until().decode("latin-1")
        if len(data) == 0:  # no data in buffers
            return None
        if len(data) < 2 or data[-2:] != "\r\n":
            self.logger.error(f'No proper line of data received. Received "{data}".')
            return None
        return data[:-2]  # remove trailing '\r\n'

    def _write(self, data):
        self.uart.write((data + "\r\n").encode("latin-1"))
