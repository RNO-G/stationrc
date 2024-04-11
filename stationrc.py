#!/usr/bin/env python3

import signal

import stationrc.bbb
import stationrc.common


def handler(signum, frame):
    if signum == signal.SIGINT:
        station.shut_down()

signal.signal(signal.SIGINT, handler)
stationrc.common.setup_logging()
station = stationrc.bbb.Station()
