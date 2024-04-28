import stationrc.common
import stationrc.remote_control

import argparse
import os

def find_nuradio():

    nuradio = None
    for path in os.environ["PYTHONPATH"].split(":"):
        if os.path.exists(f"{path}/NuRadioReco"):
            nuradio = path
            break

    assert nuradio is not None, "Could not locate NuRadioReco"
    return nuradio

def get_run(station, args):
    run = stationrc.remote_control.Run(station)

    run.run_conf.radiant_load_thresholds_from_file(False)
    run.run_conf.radiant_servo_enable(False)

    run.run_conf.radiant_trigger_rf0_enable(False)
    # run.run_conf.radiant_trigger_rf0_mask([2])
    # run.run_conf.radiant_trigger_rf0_num_coincidences(1)

    run.run_conf.radiant_trigger_rf1_enable(False)

    run.run_conf.radiant_trigger_soft_enable(True)
    run.run_conf.radiant_trigger_soft_interval(1 / args.frequency)  # 1.0 seconds btw. software triggers

    run.run_conf.flower_device_required(False)
    run.run_conf.flower_trigger_enable(False)

    run.run_conf.run_length(args.duration)  # 60 second run length

    run.run_conf.comment(args.comment)

    return run

if __name__ == "__main__":

    stationrc.common.setup_logging()

    station = stationrc.remote_control.VirtualStation()

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-f",
        "--frequency",
        type=float,
        default=1,
        help="Forced trigger triggering frequency",
    )

    parser.add_argument(
        "-t",
        "--duration",
        type=int,
        default=20,
        help="Run duration in second",
    )

    parser.add_argument(
        '-c',
        "--comment",
        type=str,
        default="Test run steered from daq_run.py",
        nargs="?",
        help=""
    )
    # parser.add_argument(
    #     "--output_dir",
    #     type=str,
    #     default=None,
    #     nargs="?",
    #     help="Move / Rename output dir"
    # )

    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        nargs="?",
        help=""
    )

    parser.add_argument(
        '-eb',
        "--eventbrowser",
        action="store_true",
        help=""
    )

    args = parser.parse_args()

    run = get_run(station, args)

    data_dir = run.start(delete_src=True, rootify=True)
    print(f"Data copied to '{data_dir}'.")
    if args.filename is not None:
        print(f"mv {data_dir}/combined.root {data_dir}/{args.filename}_combined.root")
        os.system(f"mv {data_dir}/combined.root {data_dir}/{args.filename}_combined.root")

    if args.eventbrowser:
        nuradio = find_nuradio()
        eb_exe = f"{nuradio}/NuRadioReco/eventbrowser/index.py"
        if not os.path.exists(eb_exe):
            raise FileExistsError("Could not locate eventbrowser")

        os.system(f"python3 {eb_exe} {data_dir} --rnog_file")
