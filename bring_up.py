import json

import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

station.radiant_setup()
with open(f"peds_{station.get_radiant_board_dna():016x}.json", "w") as f:
    json.dump(station.radiant_pedestal_get(), f)
