#!/bin/bash

set -eu

sudo kill $(cat /tmp/switch_server_feeder_pid.txt) || echo "No server running."

python /home/mgeorg/wakeup/switch_server_feeder.py
