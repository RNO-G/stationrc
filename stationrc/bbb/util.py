from .ControllerBoard import ControllerBoard
import sys, os, time

def on_bbb():
    return os.path.exists("/dev/ttyRadiant")

def power_cycle_radiant():
    if not on_bbb():
        sys.exit("Need to call this function on the BBB!")

    controller = ControllerBoard("/dev/ttyController")
    controller.run_command("#RADIANT-OFF", read_response=False)
    time.sleep(2)
    controller.run_command("#RADIANT-ON", read_response=False)
    controller.shut_down()