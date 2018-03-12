#!/bin/bash

set -eu

bash /home/mgeorg/wakeup/scripts/alarm.sh
bash /home/mgeorg/wakeup/scripts/warn.sh \
    "Get ready to meditate in 7 minutes" "5" \
    "2 minutes left" "2"
bash /home/mgeorg/wakeup/scripts/meditation_session.sh 35 10

