import gzip
import struct


class RawDataFile(object):
    def __init__(self, filename):
        if filename.endswith(".gz"):
            self.file = gzip.open(filename)
        else:
            self.file = open(filename, "rb")

    def multiread_int16(self, length):
        return self._multiread("h", length * 2)

    def multiread_uint8(self, length):
        return self._multiread("B", length)

    def multiread_uint16(self, length):
        return self._multiread("H", length * 2)

    def multiread_uint32(self, length):
        return self._multiread("I", length * 4)

    def read_char(self):
        return self._read("c", 1)

    def read_double(self):
        return self._read("d", 8)

    def read_float(self):
        return self._read("f", 4)

    def read_int8(self):
        return self._read("b", 1)

    def read_int16(self):
        return self._read("h", 2)

    def read_int32(self):
        return self._read("i", 4)

    def read_uint8(self):
        return self._read("B", 1)

    def read_uint16(self):
        return self._read("H", 2)

    def read_uint32(self):
        return self._read("I", 4)

    def read_uint64(self):
        return self._read("Q", 8)

    def _multiread(self, fmt, nbytes):
        try:
            return [i[0] for i in struct.iter_unpack(f"<{fmt}", self.file.read(nbytes))]
        except struct.error:
            raise EOFError

    def _read(self, fmt, nbytes):
        try:
            return struct.unpack(f"<{fmt}", self.file.read(nbytes))[0]
        except struct.error:
            raise EOFError
