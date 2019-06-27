#!/bin/bash

set -eu

SESSION_LENGTH=30
WARNING_TIME=5
BELL='/home/mgeorg/wakeup/data/bell.wav'

if [[ "$#" > "0" ]] ; then
  SESSION_LENGTH=$1
fi
if [[ "$#" > "1" ]] ; then
  WARNING_TIME=$2
fi

amixer set PCM -- 40%
date +"It is %R, meditation will be $SESSION_LENGTH minutes long" | festival --tts
sleep 1
date -d "${SESSION_LENGTH}min" +"Meditation stops at %R" | festival --tts
sleep 15

(
aplay $BELL &
sleep $(expr 6 '+' "$RANDOM" '%' '3')"."$($RANDOM '%' '10')
aplay $BELL &
sleep $(expr 6 '+' "$RANDOM" '%' '3')"."$($RANDOM '%' '10')
aplay $BELL &
) &

if [[ ${WARNING_TIME} == '0' ]] ; then
  sleep $(expr '60' '*' '(' "${SESSION_LENGTH}" ')')
else
  sleep $(expr '60' '*' '(' "${SESSION_LENGTH}" '-' "${WARNING_TIME}" ')')
  echo "Don't worry, I didn't forget about you, ${WARNING_TIME} more minutes" | festival --tts
  sleep $(expr '60' '*' "${WARNING_TIME}")
fi

aplay $BELL &
sleep $(expr 2 '+' "$RANDOM" '%' '2')"."$($RANDOM '%' '10')
aplay $BELL &

sleep 15
date +"It is %R on %B \
$(python /home/mgeorg/wakeup/ordinal.py $(date +"%d"))" | festival --tts


