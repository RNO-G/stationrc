import libconf
import pathlib


class RunConfig(object):
    def __init__(self, conf):
        self.conf = conf

    def __getitem__(self, key):
        return self.conf[key]

    def __iter__(self):
        return iter(self.conf)

    def __setitem__(self, key, value):
        self.conf[key] = value

    def comment(self, value):
        self["output"]["comment"] = str(value)

    def flower_device_required(self, value=True):
        if value:
            self["lt"]["device"]["required"] = 1
        else:
            self["lt"]["device"]["required"] = 0

    def flower_trigger_enable(self, value=True):
        if value:
            self["lt"]["trigger"]["enable_rf_trigger"] = 1
            self["radiant"]["trigger"]["ext"]["enabled"] = 1
        else:
            self["lt"]["trigger"]["enable_rf_trigger"] = 0
            self["radiant"]["trigger"]["ext"]["enabled"] = 0

    def flower_pps_trigger_enable(self, value=True):
        if value:
            self["lt"]["trigger"]["enable_pps_trigger_sys_out"] = 1
            self["radiant"]["trigger"]["ext"]["enabled"] = 1
        else:
            self["lt"]["trigger"]["enable_pps_trigger_sys_out"] = 0
            self["radiant"]["trigger"]["ext"]["enabled"] = 0

    def flower_pps_trigger_delay(self, value):
        self["lt"]["trigger"]["pps_trigger_delay"] = value

    def radiant_analog_diode_vbias(self, ch, value):
        self["radiant"]["analog"]["diode_vbias"][ch] = value

    def radiant_load_thresholds_from_file(self, value=True):
        if value:
            self["radiant"]["thresholds"]["load_from_threshold_file"] = 1
        else:
            self["radiant"]["thresholds"]["load_from_threshold_file"] = 0

    def radiant_servo_enable(self, value=True):
        if value:
            self["radiant"]["servo"]["enable"] = 1
        else:
            self["radiant"]["servo"]["enable"] = 0

    def radiant_threshold_initial(self, ch, value):
        self["radiant"]["thresholds"]["initial"][ch] = value

    def radiant_trigger_rf0_enable(self, value=True):
        if value:
            self["radiant"]["trigger"]["RF0"]["enabled"] = 1
        else:
            self["radiant"]["trigger"]["RF0"]["enabled"] = 0

    def radiant_trigger_rf0_mask(self, channels):
        mask = 0
        for ch in channels:
            mask |= 1 << ch
        self["radiant"]["trigger"]["RF0"]["mask"] = mask

    def radiant_trigger_rf0_num_coincidences(self, value):
        self["radiant"]["trigger"]["RF0"]["num_coincidences"] = value

    def radiant_trigger_rf1_enable(self, value=True):
        if value:
            self["radiant"]["trigger"]["RF1"]["enabled"] = 1
        else:
            self["radiant"]["trigger"]["RF1"]["enabled"] = 0

    def radiant_trigger_rf1_mask(self, channels):
        mask = 0
        for ch in channels:
            mask |= 1 << ch
        self["radiant"]["trigger"]["RF1"]["mask"] = mask

    def radiant_readout_mask(self, channels):
        if isinstance(channels, int):
            channels = [channels]

        mask = 0
        for ch in channels:
            mask |= 1 << ch
        self["radiant"]["readout"]["readout_mask"] = mask

    def radiant_trigger_rf1_num_coincidences(self, value):
        self["radiant"]["trigger"]["RF1"]["num_coincidences"] = value

    def radiant_trigger_soft_enable(self, value=True):
        if value:
            self["radiant"]["trigger"]["soft"]["enabled"] = 1
        else:
            self["radiant"]["trigger"]["soft"]["enabled"] = 0

    def radiant_trigger_soft_interval(self, value):
        self["radiant"]["trigger"]["soft"]["interval"] = float(value)

    def run_length(self, value):
        self["output"]["seconds_per_run"] = int(value)

    def calib_enable_cal(self, value):
        value = int(value)
        assert value in [0, 1], f"Value has to be either 0 or 1 but is {value}"
        self["calib"]["enable_cal"] = value

    def calib_set_rev(self, value):
        self["calib"]["rev"] = value

    def calib_set_channel(self, value):
        valid = ["none", "coax", "fiber0", "fiber1"]
        assert value in valid, f"Value has to in {valid} but is {value}"
        self["calib"]["channel"] = value

    def calib_set_type(self, value):
        valid = ["none", "pulser", "vco", "vco2"]
        assert value in valid, f"Value has to in {valid} but is {value}"
        self["calib"]["type"] = value

    def calib_set_attenuation(self, value):
        # Attenuation in dB (max 31.5, in steps of 0.5 dB)
        self["calib"]["atten"] = value

    @staticmethod
    def load_config(filename):
        with open(filename, "r") as f:
            conf = libconf.load(f)
        return RunConfig(conf)

    @staticmethod
    def load_default_config():
        return RunConfig.load_config(
            pathlib.Path(__file__).parent / "conf/acq.default.cfg"
        )

    def save(self, filename, replace=False):
        if not replace:
            if pathlib.Path(filename).exists():
                raise RuntimeError(f"File {filename} already exists.")
        with open(filename, "w") as f:
            libconf.dump(self.conf, f)
