from stationrc.bbb.ControllerBoard import ControllerBoard, run_command_controller_board
import sys, os, time

def on_bbb():
    return os.path.exists("/dev/ttyRadiant")

def power_cycle_radiant():
    if not os.path.exists("/dev/ttyController"):
        sys.exit("Need to call this function on the BBB!")

    run_command_controller_board("#RADIANT-OFF", read_response = False)
    time.sleep(2)
    run_command_controller_board("#RADIANT-ON", read_response = False)
