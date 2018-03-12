#!/bin/bash

set -eu

bash /home/mgeorg/wakeup/scripts/alarm.sh
bash /home/mgeorg/wakeup/scripts/warn.sh \
    "Get ready to go to the Zen Center" "5" \
    "You should be up at this point" "1"

