import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()
station.radiant_sig_gen_off()
station.radiant_calselect(quad=None)
