import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

data = station.get_controller_board_monitoring()
print(data)

data = station.get_radiant_board_id()
print(data)
