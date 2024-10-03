from stationrc.bbb.ControllerBoard import ControllerBoard, check_if_controller_console_is_open

import sys, os, subprocess

def power_cycle_radiant():

    def run_command(cmd):
        cmd = f'(read -n60 -t2 RESP < /dev/ttyController ; echo $RESP) & sleep 0.1 ; echo "{cmd}" > /dev/ttyController'
        response = subprocess.run(cmd, shell = True, executable = "/bin/bash", stdout = subprocess.PIPE)
        return response.stdout.decode("utf-8").strip()

    if check_if_controller_console_is_open():
            sys.exit("Controller console is open. Please close it before running this script.")

    if not os.path.exists("/dev/ttyController"):
        sys.exit("Need to call this function on the BBB!")

    print(run_command("#RADIANT-OFF"))
    os.system('sleep 2')
    print(run_command("#RADIANT-ON"))

