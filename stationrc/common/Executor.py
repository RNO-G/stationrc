import logging
import subprocess
import threading


class Executor(object):
    def __init__(self, cmd, logger=logging.getLogger("root")):
        self.logger = logger

        self.do_run = True
        self.proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        self.th_stdout = threading.Thread(target=Executor.read_stdout, args=[self])
        self.th_stdout.start()

        self.th_stderr = threading.Thread(target=Executor.read_stderr, args=[self])
        self.th_stderr.start()

    def read_stderr(self):
        while self.do_run:
            data = self.proc.stderr.readline().decode("latin-1")[
                :-1
            ]  # remove trailing '\n'
            if len(data) > 0:
                self.logger.error(data)
            else:
                self.logger.debug("No data on stderr.")

    def read_stdout(self):
        while self.do_run:
            data = self.proc.stdout.readline().decode("latin-1")[
                :-1
            ]  # remove trailing '\n'
            if len(data) > 0:
                self.logger.info(data)
            else:
                self.logger.debug("No data on stdout.")

    def terminate(self):
        self.proc.terminate()
        self.wrap_up()

    def wait(self):
        self.proc.wait()
        self.wrap_up()

    def wrap_up(self):
        self.do_run = False
        self.th_stdout.join()
        self.th_stderr.join()
