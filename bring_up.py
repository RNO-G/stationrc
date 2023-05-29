import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

station.radiant_setup()
station.radiant_tune_initial(reset=False, mask=0xFFFFFF)
