import enum
import json
import numpy as np
import pathlib

from .RawDataFile import RawDataFile


DAQSTATUS_MAGIC = 0xDACC
HEADER_MAGIC = 0xEAD1
PEDESTAL_MAGIC = 0x57A1
WAVEFORM_MAGIC = 0xAFD1


class PacketType(enum.Enum):
    DAQSTATUS = DAQSTATUS_MAGIC
    HEADER = HEADER_MAGIC
    PEDESTAL = PEDESTAL_MAGIC
    WAVEFORM = WAVEFORM_MAGIC


class RNOGDataFile(RawDataFile):
    RNO_G_NUM_LT_CHANNELS = 4
    RNO_G_NUM_RADIANT_CHANNELS = 24
    RNO_G_LAB4D_NSAMPLES = 4096
    RNO_G_PEDESTAL_NSAMPLES = RNO_G_LAB4D_NSAMPLES

    def __init__(self, filename):
        super(RNOGDataFile, self).__init__(filename)
        with open(
            pathlib.Path(__file__).parent / "conf" / "rno-g_data_format.json", "r"
        ) as f:
            self.data_format = json.load(f)

    def get_next_packet(self):
        try:
            magic = PacketType(self.read_uint16()).name
            version = self.read_uint16()
            packet = self.read_packet(magic, version)
            packet["_checksum"] = self.read_uint32()
            return packet
        except EOFError:
            return None

    def read_packet(self, type, version):
        version = f"v{version}"
        
        if not type in self.data_format:
            raise ValueError(f"Packet type {type} not supported.")
        
        if not version in self.data_format[type]:
            raise ValueError(f"{type} packet version {version} not supported.")
        
        data = {"type": type}
        for field in self.data_format[type][version]:

            if len(field) == 2:
                fcn = getattr(self, f"read_{field[1]}")
                data[field[0]] = fcn()
            
            elif len(field) == 3:
                fcn = getattr(self, f"multiread_{field[1]}")
                shape = list()
                
                for n in field[2]:
                    if isinstance(n, str):
                        if n.startswith("$"):
                            shape.append(data[n[1:]])
                        else:
                            shape.append(getattr(self, n))
                    elif isinstance(n, int):
                        shape.append(n)
                    else:
                        raise ValueError(f"Bad data format: {field}.")
                
                length = 1
                for n in shape:
                    length *= n
                
                arr = np.asarray(fcn(length), dtype=getattr(np, field[1]))
                data[field[0]] = arr.reshape(shape)
            else:
                raise ValueError(f"Bad data format: {field}.")

        return data

    def read_rno_g_calpulser_info(self):
        return self.read_packet("RNO-G_CALPULSER_INFO", version=0)

    def read_rno_g_lt_scaler_group(self):
        return self.read_packet("RNO-G_LT_SCALER_GROUP", version=0)

    def read_rno_g_lt_scalers(self):
        return self.read_packet("RNO-G_LT_SCALERS", version=0)

    def read_rno_g_radiant_voltages(self):
        return self.read_packet("RNO-G_RADIANT_VOLTAGES", version=0)

    def read_rno_g_lt_simple_trigger_config(self):
        return self.read_packet("rno_g_lt_simple_trigger_config", version=0)

    def read_rno_g_radiant_trigger_config(self):
        return self.read_packet("rno_g_radiant_trigger_config", version=0)
