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
    run = stationrc.remote_control.Run(station, config_file=args.config)

    run.run_conf.radiant_load_thresholds_from_file(False)
    run.run_conf.radiant_servo_enable(False)

    if "rf0" in args.trigger or "all" in args.trigger:
        run.run_conf.radiant_trigger_rf0_enable(True)
        # run.run_conf.radiant_trigger_rf0_num_coincidences(1)
    else:
        run.run_conf.radiant_trigger_rf0_enable(False)

    if "rf1" in args.trigger or "all" in args.trigger:
        run.run_conf.radiant_trigger_rf1_enable(True)
        # run.run_conf.radiant_trigger_rf1_num_coincidences(1)
    else:
        run.run_conf.radiant_trigger_rf1_enable(False)

    if "soft" in args.trigger or "all" in args.trigger:
        run.run_conf.radiant_trigger_soft_enable(True)
        run.run_conf.radiant_trigger_soft_interval(1 / args.frequency)  # 1.0 seconds btw. software triggers
    else:
        run.run_conf.radiant_trigger_soft_enable(False)

    run.run_conf.flower_device_required(False)
    if "flower" in args.trigger or "all" in args.trigger:
        run.run_conf.flower_trigger_enable(True)
    else:
        run.run_conf.flower_trigger_enable(False)

    if args.enable_calib:
        run.run_conf.calib_enable_cal(1)

    if args.calib_channel is not None:
        run.run_conf.calib_set_channel(args.calib_channel)

    if args.calib_type is not None:
        run.run_conf.calib_set_type(args.calib_type)

    if args.attenuation is not None:
        run.run_conf.calib_set_attenuation(args.attenuation)

    # for ch in range(24):
    #     run.run_conf.radiant_threshold_initial(ch, 0.9)

    run.run_conf.run_length(args.duration)  # 60 second run length

    run.run_conf.comment(str(args))

    return run

if __name__ == "__main__":

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
        default="",
        nargs="?",
        help=""
    )

    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Specify ip address of host. If `None`, use ip from `virtual_station_config.json`."
    )

    # parser.add_argument(
    #     "--output_dir",
    #     type=str,
    #     default=None,
    #     nargs="?",
    #     help="Move / Rename output dir"
    # )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        nargs="?",
        help=""
    )

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

    parser.add_argument(
        "--plot",
        action="store_true",
        help=""
    )


    parser.add_argument(
        "--calib_channel",
        type=str,
        choices=["none", "coax", "fiber0", "fiber1"],
        default=None,
        nargs="?",
        help=""
    )

    parser.add_argument(
        "--calib_type",
        type=str,
        choices=["none", "pulser", "vco", "vco2"],
        default=None,
        nargs="?",
        help=""
    )

    parser.add_argument(
        "--enable_calib",
        action="store_true",
        help=""
    )

    parser.add_argument(
        "-a",
        "--attenuation",
        type=float,
        default=None,
        help="Attenuation in dB (max 31.5, in steps of 0.5 dB)",
    )

    parser.add_argument(
        "--trigger",
        type=str,
        choices=["flower", "soft", "rf0", "rf1", "all"],
        default=["soft"],
        nargs="+",
        help=""
    )

    args = parser.parse_args()

    stationrc.common.setup_logging()

    station = stationrc.remote_control.VirtualStation(host=args.host)

    run = get_run(station, args)

    data_dir = run.start(delete_src=True, rootify=True)
    print(f"Data copied to '{data_dir}'.")
    if args.filename is not None:
        print(f"mv {data_dir}/combined.root {data_dir}/{args.filename}_combined.root")
        os.system(f"mv {data_dir}/combined.root {data_dir}/{args.filename}_combined.root")

    if args.plot:
        from stationrc.remote_control import plot_run_waveforms
        plot_run_waveforms(str(data_dir))

    if args.eventbrowser:
        raise NotImplementedError
        # nuradio = find_nuradio()
        # eb_exe = f"{nuradio}/NuRadioReco/eventbrowser/index.py"
        # if not os.path.exists(eb_exe):
        #     raise FileExistsError("Could not locate eventbrowser")

        # os.system(f"python3 {eb_exe} {data_dir} --rnog_file")
