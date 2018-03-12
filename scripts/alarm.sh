#!/bin/bash

set -eu

amixer set PCM -- 57%
mpg123 /home/mgeorg/wakeup/data/alarm.mp3
amixer set PCM -- 50%
sleep 2
(echo "on 3000" >> /tmp/switch_command.fifo) &
sleep 3
date +"It is %R on %B \
$(python /home/mgeorg/wakeup/ordinal.py $(date +"%d"))" | festival --tts
sleep 10
