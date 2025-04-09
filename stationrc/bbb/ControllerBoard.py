import logging
import os
import subprocess
import threading
import time
import sys

class ControllerBoard(object):
    def __init__(self, uart_device, background_sleep=5):
        self.logger = logging.getLogger("ControllerBoard")

        self.background_sleep = background_sleep
        self.do_run = True
        self.lock = threading.RLock()
        self.uart = os.open(uart_device, os.O_RDWR | os.O_NONBLOCK)

        self.thr_bkg = threading.Thread(
            target=ControllerBoard.receive_background_data, args=[self]
        )
        self.thr_bkg.start()

    def drain_buffer(self):
        with self.lock:
            while True:
                data = self._readline()
                if data is None:
                    break
                self.logger.debug(f"Drained {data} from buffer.")

    def receive_background_data(self):
        self.drain_buffer()
        while self.do_run:
            time.sleep(self.background_sleep)
            with self.lock:
                while True:
                    data = self._readline()
                    if data is None:
                        break
                    self.logger.info(data)

    def run_command(self, cmd, read_response = True):
        if read_response and check_if_controller_console_is_open():
            self.shut_down()
            sys.exit("Controller console is open. Please close it before calling `run_command_board()` with `read_response == True`.")

        self.drain_buffer()
        if not cmd.startswith("#"):  # all commands start with '#'
            cmd = "#" + cmd

        self.logger.debug(f'Sending "{cmd}" to UART')
        result = ""
        with self.lock:
            self._write(cmd)

            if not read_response:
                return result

            while True:
                data = self._readline()
                if data is None:
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
        os.close(self.uart)

    def _readline(self):
        try:
            data = os.read(self.uart, 2048).decode("latin-1")
        except BlockingIOError:  # no data in buffers
            return None
        if len(data) < 1 or data[-1] != "\n":
            self.logger.error(f'No proper line of data received. Received "{data}".')
            return None
        return data[:-1]  # remove trailing '\n'

    def _write(self, data):
        os.write(self.uart, (data + "\n").encode("latin-1"))

def check_if_controller_console_is_open():
    sp = subprocess.run("ps" + " -ef" + "| grep controller-console | grep -v grep", shell=True, capture_output=True)
    out = sp.stdout.decode("utf-8").strip('\n')

    if out == "":
        return False
    else:
        return True
