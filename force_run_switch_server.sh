#!/bin/bash

set -eu

sudo kill $(cat /tmp/switch_server_pid.txt) || echo "No server running."

python3 /home/mgeorg/wakeup/switch_server.py
