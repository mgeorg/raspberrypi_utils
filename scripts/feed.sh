#!/bin/bash

set -eu

echo "feed 5" >> /tmp/feeder_command.fifo

s-nail -s "Scarfie's Feeder" \
  -r 'Scarfie'\''s Feeder <manfred.georg.automated@gmail.com>' \
  "manfred.georg@gmail.com"

