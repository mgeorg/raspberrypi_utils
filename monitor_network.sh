#!/bin/bash

DATA=$(curl --silent --show-error --max-time 10 \
       http://www.google.com/generate_204 2>&1)
if [[ "$?" == "0" && -z "$DATA" ]]; then
  echo "Connected successfully."
else
  echo "Connection failed."
  (echo "network_is_down" >> /tmp/feeder_command.fifo) &
fi
