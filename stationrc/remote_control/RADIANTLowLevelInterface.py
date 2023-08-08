class RADIANTLowLevelInterface(object):
    def __init__(self, remote_control):
        self.rc = remote_control

    def calibration_specifics_get(self, channel):
        # the original dictionary uses int as keys which do not pass through the JSON sender
        data = self._send_command("radiant-calib", "lab4_specifics", {"lab": channel})
        res = dict()
        for key in data.keys():
            res[int(key)] = data[key]
        return res

    def calibration_specifics_set(self, channel, key, value):
        self.rc.send_command(
            "radiant-calib",
            "lab4_specifics_set",
            {"lab": channel, "key": key, "value": value},
        )

    def calram_base(self):
        return self.rc.send_command("radiant-calram", "get_base")

    def calram_mode(self, mode):
        self.rc.send_command("radiant-calram", "mode_str", {"mode": mode.value})

    def calram_num_rolls(self):
        return self.rc.send_command("radiant-calram", "numRolls")

    def calram_zero(self, zerocross_only=False):
        self.rc.send_command(
            "radiant-calram", "zero", {"zerocrossOnly": zerocross_only}
        )

    def calselect(self, quad):
        return self.rc.send_command("radiant-board", "calSelect", {"quad": quad})

    def dma_base(self):
        return self.rc.send_command("radiant-dma", "get_base")

    def dma_begin(self):
        self.rc.send_command("radiant-dma", "beginDMA")

    def dma_disable(self):
        self.rc.send_command("radiant-dma", "enable", {"onoff": False})

    def dma_enable(self, mode=0):
        self.rc.send_command("radiant-dma", "enable", {"onoff": True, "mode": mode})

    def dma_read(self, length):
        return self._send_command("radiant-dma", "dmaread", {"length": length})

    def dma_set_descriptor(self, channel, address, length, increment=False, final=True):
        self.rc.send_command(
            "radiant-dma",
            "setDescriptor",
            {
                "num": channel,
                "addr": address,
                "length": length,
                "increment": increment,
                "final": final,
            },
        )

    def lab4d_controller_force_trigger(self, block=False, num_trig=1, safe=True):
        return self._send_command(
            "radiant-labc",
            "force_trigger",
            {"block": block, "numTrig": num_trig, "safe": safe},
        )

    def lab4d_controller_scan_width(self, scan_num, trials=1):
        return self._send_command(
            "radiant-labc", "scan_width", {"scanNum": scan_num, "trials": trials}
        )

    def lab4d_controller_start(self):
        self.rc.send_command("radiant-labc", "start")

    def lab4d_controller_stop(self):
        self.rc.send_command("radiant-labc", "stop")

    def lab4d_controller_tmon_set(self, channel, value):
        self.rc.send_command(
            "radiant-labc", "set_tmon", {"lab": channel, "value": value}
        )

    def lab4d_controller_update(self, channel):
        self.rc.send_command("radiant-labc", "update", {"lab4": channel})

    def lab4d_controller_write_register(self, channel, address, value, verbose=False):
        self.rc.send_command(
            "radiant-labc",
            "l4reg",
            {"lab": channel, "addr": address, "value": value, "verbose": verbose},
        )

    def monselect(self, channel):
        self.rc.send_command("radiant-board", "monSelect", {"lab": channel})

    def read_register(self, name):
        return self.rc.send_command("radiant-board", "readReg", {"name": name})
