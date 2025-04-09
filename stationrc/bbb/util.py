import sys, os, time

def on_bbb():
    return os.path.exists("/dev/ttyRadiant")
