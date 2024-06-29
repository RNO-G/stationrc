import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

if not station.rc.run_local:
    data = station.get_controller_board_monitoring()
    print(data)
else:
    print("Local run: No controller board access -> no monitoring data")

data = station.get_radiant_board_id()
print(data)
