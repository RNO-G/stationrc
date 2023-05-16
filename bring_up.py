import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

station.radiant_setup()
station.radiant_tune_initial(reset=False, mask=0xFFFFFF)
station.radiant_calib_isels(num_iterations=10, buff=32, step=4, voltage_setting=1250)
