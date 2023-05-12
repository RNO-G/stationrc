# Extract some functions copy&paste from https://github.com/RNO-G/radiant-python

import logging

from .SerialCOBSDevice import SerialCOBSDevice


class RadiantBoard(object):
    
    REGISTER = { 'FPGA_ID':          0x00,
			     'FPGA_DATEVERSION': 0x04,
     			 'BM_ID' :           0x400000,
                 'BM_DATEVERSION':   0x400004,
			     'BM_STATUS':        0x400008,
			    }
    
    def __init__(self, uart_device, uart_baudrate=1000000):
        self.logger = logging.getLogger('RadiantBoard')
        
        self.uart = SerialCOBSDevice(port=uart_device, baudrate=uart_baudrate)
    
    def get_id(self):
        bid = self._decode_id(self.uart.read(self.REGISTER['BM_ID']))
        bver = self._decode_dateversion(self.uart.read(self.REGISTER['BM_DATEVERSION']))
        status = self.uart.read(self.REGISTER['BM_STATUS'])
        fid = self._decode_id(self.uart.read(self.REGISTER['FPGA_ID']))
        fver = self._decode_dateversion(self.uart.read(self.REGISTER['FPGA_DATEVERSION']))
        return { 'board_manager_id': bid,
                 'board_manager_version': bver,
                 'board_manager_status': status,
                 'fpga_id': fid,
                 'fpga_version': fver }
    
    @staticmethod
    def _decode_dateversion(val):
        major = (val >> 12) & 0xF
        minor = (val >> 8) & 0xF
        revision = (val & 0xFF)
        day = (val >> 16) & 0x1F
        month = (val >> 21) & 0xF
        year = (val >> 25) & 0x7F
        return { 'version': f'{major}.{minor}.{revision}', 'date': f'{year+2000}-{month:02d}-{day:02d}' }
    
    @staticmethod
    def _decode_id(val):
        res = str(chr((val >> 24) & 0xFF))
        res += chr((val >> 16) & 0xFF)
        res += chr((val >> 8) & 0xFF)
        res += chr(val & 0xFF)
        return res
