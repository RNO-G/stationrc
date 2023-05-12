import json
import logging
import pathlib
import zmq

import stationrc.common


class VirtualStation(object):
    
    def __init__(self):
        self.logger = logging.getLogger('VirtualStation')
        
        with open(pathlib.Path(__file__).parent / 'conf/virtual_station_conf.json', 'r') as f:
            self.station_conf = json.load(f)
        
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(f'tcp://{self.station_conf["remote_control"]["host"]}:{self.station_conf["remote_control"]["port"]}')
    
    def daq_run_start(self):
        return self._send_command('station', 'daq_run_start')
    
    def daq_run_terminate(self):
        self._send_command('station', 'daq_run_terminate')
    
    def daq_run_wait(self):
        self._send_command('station', 'daq_run_wait')
    
    def get_controller_board_monitoring(self):
        #TODO: parse all fields in data
        
        data = self._send_command('controller-board', '#MONITOR')
        res = { 'analog': {}, 'power': {}, 'temp': {} }
        tokens = data.split()
        res['analog']['timestamp'] = int(tokens[4][:-1])
        res['power']['timestamp'] = int(tokens[26][:-1])
        res['temp']['timestamp'] = int(tokens[43][:-1])
        return res
    
    def get_radiant_board_id(self):
        return self._send_command('radiant-board', 'get_id')
    
    def retrieve_data(self, src, delete_src=False):
        #TODO: implement removing the data on the BBB after successful rsync
        
        self.proc = stationrc.common.Executor(cmd=['rsync', '--archive', '--compress', '--verbose', '--stats', f'{self.station_conf["remote_control"]["user"]}@{self.station_conf["remote_control"]["host"]}:{src}', self.station_conf['daq']['data_directory']], logger=self.logger)
        self.proc.wait()
    
    def set_run_conf(self, conf):
        self._send_command('station', 'write_run_conf', conf.get_JSON())
    
    def _send_command(self, device, cmd, data=None):
        tx = { 'device': device, 'cmd': cmd }
        if data != None:
            tx['data'] = data
        self.logger.debug(f'Sending command: "{tx}".')
        self.socket.send_json(tx)
        message = self.socket.recv_json()
        self.logger.debug(f'Received reply: "{message}"')
        if not 'status' in message or message['status'] != 'OK':
            self.logger.error(f'Sent: "{tx}". Received: "{message}"')
            return None
        if not 'data' in message:
            return None
        return message['data']
