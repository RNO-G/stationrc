import json
import logging
import zmq


class RemoteControl(object):
    def __init__(self, host, port):
        self.logger = logging.getLogger("RemoteControl")

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        socket = f"tcp://{host}:{port}"
        self.logger.info(f"Connect to socket: '{socket}'.")
        self.socket.connect(socket)

    def send_command(self, device, cmd, data=None):
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
