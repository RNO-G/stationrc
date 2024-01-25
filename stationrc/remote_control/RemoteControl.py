import json
import logging
import zmq
import socket
import pickle
import struct
import threading

def get_ip():
    soc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    soc.settimeout(0)
    try:
        # doesn't even have to be reachable
        soc.connect(('10.254.254.254', 1))
        ip = soc.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        soc.close()
    return ip


def handleLogRecord(record):

    # N.B. EVERY record gets logged. This is because Logger.handle
    # is normally called AFTER logger-level filtering. If you want
    # to do filtering, do it at the client end to save wasting
    # cycles and network bandwidth!
    logger = logging.getLogger(record.name)
    logger.handle(record)


class RemoteControl(object):
    def __init__(self, host, port, logger_port):
        self.logger = logging.getLogger("RemoteControl")

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        socket_add = f"tcp://{host}:{port}"
        self.logger.info(f"Connect to socket: '{socket_add}'.")
        self.socket.connect(socket_add)

        # self.logger_socket = socket.create_server((get_ip(), logger_port), reuse_port=True)  # get instance
        self.logger_socket = socket.socket()
        self.logger_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.logger_socket.bind(("", logger_port))  # bind to all interfaces
        self.logger.info(f"Listening to logging on port {logger_port}")

        # configure how many client the server can listen simultaneously
        self.logger_socket.listen(1)

        self.listening = True
        self.thr_logger = threading.Thread(
            target=self.receive_logger,  daemon=True)  # daemon=True -> dies when program finishes
        self.thr_logger.start()

        self._logger_port = logger_port
        self._has_set_logger = False

    def send_command(self, device, cmd, data=None):
        tx = {"device": device, "cmd": cmd}
        if data is not None:
            tx["data"] = json.dumps(data)

        if device != "controller-board" and not self._has_set_logger:
            self._has_set_logger = True
            self.set_remote_logger_handler()

        self.logger.debug(f'Sending command: "{tx}".')
        self.socket.send_json(tx)

        message = self.socket.recv_json()
        self.logger.debug(f'Received reply: "{message}"')

        if "status" not in message or message["status"] != "OK":
            if "data" in message and message["data"] == "Catched a cobs.DecodeError":
                self.logger.error(f"Decoder Error. You likely have to restart the deamon on the BBB. (Sent: \"{tx}\")")
                raise ValueError(f"Decoder Error. You likely have to restart the deamon on the BBB. (Sent: \"{tx}\")")
            else:
                self.logger.error(f'Sent: "{tx}". Received: "{message}"')
                return None

        if "data" not in message:
            return None

        return message["data"]

    def receive_logger(self):

        self.conn, _ = self.logger_socket.accept()  # accept new connection

        while self.listening:
            chunk = self.conn.recv(4)
            if len(chunk) < 4:
                break

            slen = struct.unpack('>L', chunk)[0]
            chunk = self.conn.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.conn.recv(slen - len(chunk))

            obj = pickle.loads(chunk)
            handleLogRecord(logging.makeLogRecord(obj))

        print("End of receive_logger")

    def set_remote_logger_handler(self):
        self.logger.info("Set remote logger handler")
        return self.send_command("radiant-board", "add_logger_handler",
                                 {"host": get_ip(), "port": self._logger_port})
