import json
import libconf
import logging
import pathlib
import subprocess
import threading
import zmq

import stationrc.common
import stationrc.radiant
from .ControllerBoard import ControllerBoard


class Station(object):
    
    def __init__(self):
        self.logger = logging.getLogger('Station')
        
        with open(pathlib.Path(__file__).parent / 'conf/station_conf.json', 'r') as f:
            self.station_conf = json.load(f)
        
        self.controller_board = ControllerBoard(uart_device=self.station_conf['daq']['controller_board_dev'], uart_baudrate=self.station_conf['daq']['controller_board_baudrate'])
        
        self.radiant_board = stationrc.radiant.RADIANT(port=self.station_conf['daq']['radiant_board_dev'])
        
        self.thr_rc = threading.Thread(target=Station.receive_remote_command, args=[self])
        self.thr_rc.start()
    
    def daq_run_start(self):
        data_dir = self.get_data_dir()
        self.acq_proc = stationrc.common.Executor(cmd='/rno-g/bin/rno-g-acq', logger=self.logger)
        return { 'data_dir': str(data_dir) }
    
    def daq_run_terminate(self):
        self.acq_proc.terminate()
    
    def daq_run_wait(self):
        self.acq_proc.wait()
    
    def get_data_dir(self):
        with open(self.station_conf['daq']['run_conf'], 'r') as f:
            conf = libconf.load(f)
        with open(conf['output']['runfile'], 'r') as f:
            runnumber = int(f.readline())
        return pathlib.Path(conf['output']['base_dir']) / f'run{runnumber}'
    
    def receive_remote_command(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(f'tcp://*:{self.station_conf["remote_control"]["port"]}')
        
        while True:
            message = socket.recv_json()
            self.logger.debug(f'Received remote command: "{message}".')
            if not ('device' in message and 'cmd' in message):
                self.logger.error(f'Received malformed command: "{message}".')
                socket.send_json({ 'status': 'ERROR' })
            
            elif message['device'] == 'controller-board':
                res = self.controller_board.run_command(message['cmd'])
                socket.send_json({ 'status': 'OK', 'data': res })
            
            elif message['device'] in ['radiant-board', 'station']:
                if message['device'] == 'radiant-board':
                    dev = self.radiant_board
                elif message['device'] == 'station':
                    dev = self
                
                if hasattr(dev, message['cmd']):
                    func = getattr(dev, message['cmd'])
                    if 'data' in message:
                        data = json.loads(message['data'])
                        res = func(data)
                    else:
                        res = func()
                    if res != None:
                        socket.send_json({ 'status': 'OK', 'data': res })
                    else:
                        socket.send_json({ 'status': 'OK' })
                else:
                    socket.send_json({ 'status': 'UNKNOWN' })
            
            else:
                socket.send_json({ 'status': 'UNKNOWN' })
    
    def write_run_conf(self, data):
        with open(self.station_conf['daq']['run_conf'], 'w') as f:
            libconf.dump(data, f)
