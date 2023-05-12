import stationrc.common
import stationrc.remote_control


stationrc.common.setup_logging()

station = stationrc.remote_control.VirtualStation()

run = stationrc.remote_control.Run(station)
run.run_conf.radiant_load_thresholds_from_file(False)
run.run_conf.radiant_servo_enable(False)
run.run_conf.radiant_trigger_rf0_enable(False)
run.run_conf.radiant_trigger_rf1_enable(False)
run.run_conf.radiant_trigger_soft_enable(True)
run.run_conf.radiant_trigger_soft_interval(1.0) # 1.0 seconds btw. software triggers
run.run_conf.flower_device_required(False)
run.run_conf.flower_trigger_enable(False)
run.run_conf.run_length(60) # 60 second run length
run.run_conf.comment('Test run steered from daq_run.py')
run.start(rootify=True)
