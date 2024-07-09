Hi guys, I think I found an elegant way to use stationrc in the field. The idea is to use stationrc on the bbb without the need to keep a deamon running in the background which receivs the commands. I will demonstrate what I did with some pseudo code example.

This is in a nutshell how stationrc works right now. There is a call `stationrc.bbb.Station` which allows to receive commads send via zmq and executes them on the bbb and sends the result back to the remote pc. I have seperated the functions which parses the send command message and executes the command from the function which receives the command message and sends back the results.

```
class Station(object):
    def __init__(self):
        ...

        self.thr_rc = threading.Thread(
            target=Station._receive_remote_command, args=[self])
        self.thr_rc.start()

def _receive_remote_command(self):
    context = zmq.Context()
    socket = context.socket(zmq.REP)

    while True:
        message = socket.recv_json()
        status, data = self.parse_message_execute_command(message)
        socket.send_json({"status": status, "data": data})
```

To send a command from the remote pc one has the class `stationrc.remote_control.RemoteControl`:

```
class RemoteControl(object):
    def __init__(self, host, port, logger_port):

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)

    def send_command(self, device, cmd, data=None):
        tx = {"device": device, "cmd": cmd}
        if data is not None:
            tx["data"] = json.dumps(data)

        self.logger.debug(f'Sending command: "{tx}".')
        self.socket.send_json(tx)

        message = self.socket.recv_json()
```

What I did is to implement a "local" mode which in `stationrc.remote_control.RemoteControl` initializes an object of `stationrc.bbb.Station` and executes the function `self.station.parse_message_execute_command(tx)` instead of `self.socket.send_json(tx)`. `stationrc.bbb.Station` does not start a thread (deamon) which listening to receive commands.

```
class Station(object):
    def __init__(self, start_thread=True):
        ...
        if start_thread:
            self.thr_rc = threading.Thread(
                target=Station._receive_remote_command, args=[self])
            self.thr_rc.start()

class RemoteControl(object):
    def __init__(self, host, port, logger_port, run_local=False):
        self.run_local = run_local
        if self.run_local:
            self.station = Station(start_thread=False)

    def send_command(self, device, cmd, data=None):
        tx = {"device": device, "cmd": cmd}
        if data is not None:
            tx["data"] = json.dumps(data)

        if self.run_local:
            status, data = self.station.parse_message_execute_command(tx)
            message = {"status": status, "data": data}

        else:
            self.logger.debug(f'Sending command: "{tx}".')
            self.socket.send_json(tx)

            message = self.socket.recv_json()
```
