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
        self['output']['comment'] = str(value)
    
    def flower_device_required(self, value=True):
        if value:
            self['lt']['device']['required'] = 1
        else:
            self['lt']['device']['required'] = 0
    
    def flower_trigger_enable(self, value=True):
        if value:
            self['lt']['trigger']['enable_rf_trigger'] = 1
            self['radiant']['trigger']['ext']['enabled'] = 1
        else:
            self['lt']['trigger']['enable_rf_trigger'] = 0
            self['radiant']['trigger']['ext']['enabled'] = 0
    
    def radiant_load_thresholds_from_file(self, value=True):
        if value:
            self['radiant']['thresholds']['load_from_threshold_file'] = 1
        else:
            self['radiant']['thresholds']['load_from_threshold_file'] = 0
    
    def radiant_servo_enable(self, value=True):
        if value:
            self['radiant']['servo']['enable'] = 1
        else:
            self['radiant']['servo']['enable'] = 0
    
    def radiant_threshold_initial(self, ch, value):
        self['radiant']['thresholds']['initial'][ch] = value

    def radiant_trigger_rf0_enable(self, value=True):
        if value:
            self['radiant']['trigger']['RF0']['enabled'] = 1
        else:
            self['radiant']['trigger']['RF0']['enabled'] = 0
    
    def radiant_trigger_rf0_mask(self, channels):
        mask = 0
        for ch in channels:
            mask |= (1 << ch)
        self['radiant']['trigger']['RF0']['mask'] = mask

    def radiant_trigger_rf0_num_coincidences(self, value):
        self['radiant']['trigger']['RF0']['num_coincidences'] = value

    def radiant_trigger_rf1_enable(self, value=True):
        if value:
            self['radiant']['trigger']['RF1']['enabled'] = 1
        else:
            self['radiant']['trigger']['RF1']['enabled'] = 0

    def radiant_trigger_rf1_enable(self, value=True):
        if value:
            self['radiant']['trigger']['RF1']['enabled'] = 1
        else:
            self['radiant']['trigger']['RF1']['enabled'] = 0
    
    def radiant_trigger_rf1_mask(self, channels):
        mask = 0
        for ch in channels:
            mask |= (1 << ch)
        self['radiant']['trigger']['RF1']['mask'] = mask

    def radiant_trigger_soft_enable(self, value=True):
        if value:
            self['radiant']['trigger']['soft']['enabled'] = 1
        else:
            self['radiant']['trigger']['soft']['enabled'] = 0
    
    def radiant_trigger_soft_interval(self, value):
        self['radiant']['trigger']['soft']['interval'] = float(value)
    
    def run_length(self, value):
        self['output']['seconds_per_run'] = int(value)
    
    @staticmethod
    def load_config(filename):
        with open(filename, 'r') as f:
            conf = libconf.load(f)
        return RunConfig(conf)
    
    @staticmethod
    def load_default_config():
        return RunConfig.load_config(pathlib.Path(__file__).parent / 'conf/acq.default.cfg')
    
    def save(self, filename, replace=False):
        if not replace:
            if pathlib.Path(filename).exists():
                raise RuntimeError(f'File {filename} already exists.')
        with open(filename, 'w') as f:
            libconf.dump(self.conf, f)
