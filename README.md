# stationrc - Remote control of RNO-G stations

`stationrc` is a Python framework to control RNO-G stations, i.e. configure them and take data using a unified interface on a control PC without the need to log into the Beagle Bone Black and interact with all the different scripts and executables there. It is mainly developed as basis for the [radiant-test](https://github.com/RNO-G/radiant-test) repository for production testing of new RADIANT boards but might also be helpful for station calibration and characterization in the lab.

The `stationrc` Python library must be available on both, the Beagle Bone Black and the control PC. `stationrc` pulls in the stationrc branch of the [radiant-python](https://github.com/RNO-G/radiant-python/tree/stationrc) as git submodule, so when cloning to your local machine you need to run

```
git clone git@github.com:RNO-G/stationrc.git
git submodule init
git submodule update
```

`VirtualStation.py` is the abstract station interface on the control PC that normal users and the testing framework will interact with. `VirtualStation.py` is not complete and is always extended with more functionality as needed.

`Run.py`: uses `rno-g-acq` on the BBB to acquire data. Runs are configured via a [RunConfig](https://github.com/RNO-G/stationrc/blob/main/stationrc/remote_control/RunConfig.py) object and data are automtically moved to the Control PC and rootified using mattak.

`Station.py` is the realization of the interface running on the Beagle Bone Black.

The file `stationrc/common/conf/logging.conf` configures the Python logging system. It is currently configured to print *all* messages to the screen. Later, it can easily be adapted to log e.g. `DEBUG` messages only to (rotating) log files.

## On the Beagle Bone Black (BBB)

Install the Python packages for zeroMQ (communication to control PC) and libconf (read/write DAQ configuration files):

`pip3 install --user pyzmq`

`pip3 install --user libconf`

The file `stationrc/bbb/conf/station.conf` stores some low-level configuration parameters. No changes should be needed here.

`stationrc.py` is the leight-weight demon to run on the BBB. It also replaces the `controller-console` script to control the station. By default, it listens for commands on IP port 8000. You can execute it with `python3 stationrc.py`, and it will start listening to commands from the Control PC.

If you get an error like

```
Traceback (most recent call last):
  File "stationrc.py", line 8, in <module>
    station = stationrc.bbb.Station()
  File "/home/rno-g/stationrc/stationrc/bbb/Station.py", line 27, in __init__
    self.radiant_board = stationrc.radiant.RADIANT(
AttributeError: module 'stationrc.radiant' has no attribute 'RADIANT'
```

probably you have not properly pulled the git submodule in `stationrc/radiant/`. Did you run `git submodule update --recursive --remote` in the repository?

## On the Control PC

Install the same packages as on the BBB

The file `stationrc/remote_control/conf/virtual_station.conf` stores configuration parameters for connecting to the BBB and paths to data and tools. By default the repositoy contains `stationrc/remote_control/conf/virtual_station_default.conf` which is used when `virtual_station.conf` does not exist. Copy `virtual_station_default.conf` and update it to your configuration before running any of the examples.

So far, not the full API / Interface have been implemented. There is a minimal subset of commands to demonstrate the idea behind `stationrc`.

### Example scripts

1. Interaction with the controller board (switching on/off the RADIANT, amplifiers, ...; getting status information). The full set of commands is listed [here](https://github.com/RNO-G/control-uC/blob/352040e116d034586e8e8c1848d80a4b9bafe6ea/docs/DESIGN.commands)

```
python3 controller-board-rc.py '#MONITOR'

 #MONITOR: analog: { when: 3825267, temp: 25.47 C, i_surf3V: [4,6,6,4,4,4] mA, i_down3v: [4,4,4] mA, i_sbc5v: 216, i_radiant: 2749 mA, i_lt: 9 mA}
 #MONITOR: power: { when: 3825267, PV_V: 0.85 V, PV_I: 0 mA, BAT_V: 15.12 V, BAT_I: 1090 mA}
 #MONITOR: temp: { when: 3825267, local: 26.625 C, remote1: -64.0 C, remote2: -64.0}
 #MONITOR: power_state: { low_power: 0, sbc_power: 1, lte_power: 0, radiant_power: 1, lowthresh_power: 0, dh_amp_power: 0, surf_amp_power: 0}
```

2. Interaction with the RADIANT (using code borrowed from `radiant-python`) and the controller board for slow control and configuration. This is just a random example and the interface needs expansion

```
python3 station_status.py

 {'analog': {'timestamp': 3825387}, 'power': {'timestamp': 3825387}, 'temp': {'timestamp': 3825387}}
 {'board_manager_id': 'RDBM', 'board_manager_version': {'version': '0.2.10', 'date': '2022-03-30'}, 'board_manager_status': 251, 'fpga_id': 'RDNT', 'fpga_version': {'version': '0.3.3', 'date': '2021-09-06'}}
```

3. Configure a run and take data. This will create the run configuration file on the BBB, execute the run, and copy the data to the control PC via rsync (assumes password-less access to the BBB using ssh keys). Most debugging outupt / progress will show up in the logging on the BBB.

```
python3 daq_run.py
```

See `daq_run.py` for an example how to change the run configuration. Data will be copied to `/Users/tikarg/local/RNO-G/data`.
