import json
import logging
import pathlib


class RADIANTLowLevelInterface(object):
    BOARD_MANAGER_BASE_ADDRESS = 0x400000
    NUM_CHANNELS = 24
    NUM_QUADS = 6

    def __init__(self, remote_control):
        self.logger = logging.getLogger("RADIANTLowLevelInterface")
        self.rc = remote_control

    def board_manager_status(self):
        value = self.read_register("BM_STATUS")
        res = dict()
        res["FPGA_DONE"] = bool(value & (0x1 << 0))
        res["MGTDET"] = bool(value & (0x1 << 1))
        res["SD_DETECT"] = bool(value & (0x1 << 2))
        res["POWER_GOOD_1V0"] = bool(value & (0x1 << 3))
        res["POWER_GOOD_1V8"] = bool(value & (0x1 << 4))
        res["POWER_GOOD_2V5"] = bool(value & (0x1 << 5))
        res["POWER_GOOD_2V6"] = bool(value & (0x1 << 6))
        res["POWER_GOOD_3V1"] = bool(value & (0x1 << 7))
        return res

    def board_manager_uid(self):
        res = self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x30)
        res += self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x34) << 32
        res += self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x38) << 64
        res += self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x3C) << 96
        return res

    def board_manager_uptime(self):
        time_low = self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0xE8)
        time_high = self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0xEC)
        return (time_high << 32) + time_low

    def board_manager_voltage_readback(self):
        res = dict()
        res["VOLTAGE_1V0"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x10) / 65535 * 3.3
        )
        res["VOLTAGE_1V8"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x14) / 65535 * 3.3
        )
        res["VOLTAGE_2V5"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x18) / 65535 * 3.3
        )
        res["VOLTAGE_2V6"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x1C) / 65535 * 3.3
        )
        res["VOLTAGE_3V1"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x20) / 65535 * 3.3
        )
        return res

    def calibration_load(self):
        self.logger.info(f"Loading calibration for board {self.board_manager_uid():032x}")
        self.rc.send_command(
            "radiant-calib", "load", {"uid": self.board_manager_uid()})

    def calibration_load_from_local(self):
        filename = pathlib.Path(__file__).parent / ".." / ".." / "calib" / \
            f"cal_{self.board_manager_uid():032x}.json"

        self.logger.info(f"Loading calibration: {filename}")

        if not pathlib.Path(filename).exists():
            self.logger.warning(f"File '{filename}' does not exist. Doing nothing!")
            return

        with open(filename, "r") as f:
            calib = json.load(f)

        for ch in calib.keys():
            for key in calib[ch].keys():
                self.calibration_specifics_set(int(ch), int(key), calib[ch][key])

    def calibration_save(self):
        self.logger.info(f"Saving calibration for board {self.board_manager_uid():032x}")
        self.rc.send_command(
            "radiant-calib", "save", {"uid": self.board_manager_uid()})

    def calibration_save_to_local(self):
        calib = dict()
        for ch in range(self.NUM_CHANNELS):
            calib[ch] = self.calibration_specifics_get(ch)

        filename = pathlib.Path(__file__).parent / ".." / ".." / "calib" / \
            f"cal_{self.board_manager_uid():032x}.json"

        self.logger.info(f"Saving calibration: {filename}")

        with open(filename, "w") as f:
            json.dump(calib, f)


    def calibration_specifics_get(self, channel):
        # the original dictionary uses int as keys which do not pass through the JSON sender
        data = self.rc.send_command("radiant-calib", "lab4_specifics", {"lab": channel})
        res = dict()
        for key in data.keys():
            res[int(key)] = data[key]
        return res

    def calibration_specifics_reset(self, channel):
        self.rc.send_command("radiant-calib", "lab4_reset_specifics", {"lab": channel})

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

    def dma_base(self):
        return self.rc.send_command("radiant-dma", "get_base")

    def dma_begin(self):
        self.rc.send_command("radiant-dma", "beginDMA")

    def dma_disable(self):
        self.rc.send_command("radiant-dma", "enable", {"onoff": False})

    def dma_enable(self, mode=0):
        self.rc.send_command("radiant-dma", "enable", {"onoff": True, "mode": mode})

    def dma_read(self, length):
        return self.rc.send_command("radiant-dma", "dmaread", {"length": length})

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

    def dna(self):
        return int(self.rc.send_command("radiant-board", "dna"))

    def lab4d_controller_automatch_phab(self, channel, match=1):
        self.rc.send_command(
            "radiant-labc", "automatch_phab", {"lab": channel, "match": match}
        )

    def lab4d_controller_autotune_vadjp(self, channel, initial=2700):
        return self.rc.send_command(
            "radiant-labc", "autotune_vadjp", {"lab": channel, "initial": initial}
        )

    def lab4d_controller_default(self, channel, initial=True):
        self.rc.send_command(
            "radiant-labc", "default", {"lab4": channel, "initial": initial}
        )

    def lab4d_controller_force_trigger(self, block=False, num_trig=1, safe=True):
        return self.rc.send_command(
            "radiant-labc",
            "force_trigger",
            {"block": block, "numTrig": num_trig, "safe": safe},
        )

    def lab4d_controller_scan_width(self, scan_num, trials=1):
        return self.rc.send_command(
            "radiant-labc", "scan_width", {"scanNum": scan_num, "trials": trials}
        )

    def lab4d_controller_scan_dump(self, lab=31):  # 31 = station.radiant_board.labc.labAll
        return self.rc.send_command("radiant-labc", "scan_dump", {"lab": lab})

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

    def pedestal_voltage_get(self):
        res = dict()
        res["VPEDLEFT"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0xE0) / 4095 * 3.3
        )
        res["VPEDRIGHT"] = (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0xE4) / 4095 * 3.3
        )
        return res

    def quad_gpio_get(self, quad):
        if quad < 0 or quad > self.NUM_QUADS - 1:
            raise ValueError(f"No quad {quad}")

        value = self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x40 + 4 * quad)
        res = dict()
        res["SEL_CAL"] = bool(value & (0x1 << 0))
        res["ATT_LE"] = bool(value & (0x1 << 1))
        res["BIST"] = bool(value & (0x1 << 2))
        res["LED_GREEN"] = bool(value & (0x1 << 3))
        res["TRIG_EN"] = bool(value & (0x1 << 4))
        res["LAB_EN"] = bool(value & (0x1 << 5))
        res["DIP_SWITCH_BIT0"] = bool(value & (0x1 << 6))
        res["DIP_SWITCH_BIT1"] = bool(value & (0x1 << 7))
        return res

    def read_register(self, addr):
        return self.rc.send_command("radiant-board", "readReg", {"addr": addr})

    def trigger_diode_bias_get(self, channel):
        if channel < 0 or channel > self.NUM_CHANNELS - 1:
            raise ValueError(f"No channel {channel}")

        return (
            self.read_register(self.BOARD_MANAGER_BASE_ADDRESS + 0x80 + 4 * channel)
            / 4095
            * 2.0
        )
