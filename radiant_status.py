import datetime

import stationrc.common
import stationrc.radiant
import stationrc.remote_control


def print_dict(d, prefix="   "):
    for key in d.keys():
        print(f"{prefix}{key}: {d[key]}")


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

print(f"RADIANT Revision: {station.radiant_revision()}")

print(f"MCU UID: {station.get_radiant_board_mcu_uid():032x}")

print(f"DNA: {station.get_radiant_board_dna():016x}")

print(f"Sample rate: {station.radiant_sample_rate()} MHz")

board_manager_id = stationrc.radiant.register_to_string(
    station.radiant_low_level_interface.read_register("BM_ID")
)
print(f"Board Manager ID: {board_manager_id}")
print(
    f"Board Manager uptime: {datetime.timedelta(milliseconds=station.radiant_low_level_interface.board_manager_uptime())}"
)

board_manager_date_version = stationrc.radiant.DateVersion(
    station.radiant_low_level_interface.read_register("BM_DATEVERSION")
).toDict()
print("Board Manager version:")
print_dict(board_manager_date_version)

board_manager_status = station.radiant_low_level_interface.board_manager_status()
print("Board Manager status:")
print_dict(board_manager_status)

board_manager_voltage_readback = (
    station.radiant_low_level_interface.board_manager_voltage_readback()
)
print("Board Manager voltage readback:")
print_dict(board_manager_voltage_readback)

quad_gpio = dict()
for quad in range(station.radiant_low_level_interface.NUM_QUADS):
    quad_gpio[quad] = station.radiant_low_level_interface.quad_gpio_get(quad)
print("Quad GPIO:")
for key in quad_gpio[0].keys():
    line = f"   {key}:\t"
    for quad in range(station.radiant_low_level_interface.NUM_QUADS):
        line += f"{quad_gpio[quad][key]}"
        if quad != station.radiant_low_level_interface.NUM_QUADS - 1:
            line += "\t"
    print(line)

trigger_diode_bias = dict()
for ch in range(station.radiant_low_level_interface.NUM_CHANNELS):
    trigger_diode_bias[ch] = station.radiant_low_level_interface.trigger_diode_bias_get(
        ch
    )
print("Trigger diode bias (V):")
line = "   "
for ch in range(station.radiant_low_level_interface.NUM_CHANNELS):
    line += f"{ch}: {trigger_diode_bias[ch]:.2f}"
    if ch != station.radiant_low_level_interface.NUM_CHANNELS - 1:
        line += ", "
print(line)

pedestal_voltage = station.radiant_low_level_interface.pedestal_voltage_get()
print("Pedestal voltage:")
print_dict(pedestal_voltage)
