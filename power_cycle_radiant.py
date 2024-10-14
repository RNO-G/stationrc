import stationrc.remote_control
import stationrc.common
import stationrc.bbb

import os, argparse, time


if __name__ == "__main__":

    stationrc.common.setup_logging()

    # Determine if we are running on the BeagleBone Black
    if stationrc.bbb.on_bbb():
        controller = stationrc.bbb.ControllerBoard("/dev/ttyController")
        controller.run_command("#RADIANT-OFF", read_response = False)
        time.sleep(2)
        controller.run_command("#RADIANT-ON", read_response = False)
        controller.shut_down()
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument("command", type=str, help="command to be sent to station")

        parser.add_argument(
            "--host", "--hosts",
            dest="hosts",
            type=str, default=[None],
            nargs="+",
            help="Specify ip address of host. If `None`, use ip from config in stationrc.")


        args = parser.parse_args()

        for host in args.hosts:
            station = stationrc.remote_control.VirtualStation(host=host)

            data = station.rc.send_command("controller-board", "#RADIANT-OFF")
            print(data)
            time.sleep(2)
            data = station.rc.send_command("controller-board", "#RADIANT-ON")
            print(data)
