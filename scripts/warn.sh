#!/bin/bash

set -eu

amixer set PCM -- 50%
while [[ "$#" > 0 ]] ; do
  echo "$1" | festival --tts
  sleep $(expr '60' '*' "$2")
  shift
  shift
done

