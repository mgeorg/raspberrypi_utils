#!/bin/bash

set -eu

# Ensure all subprocess commands terminate.
trap 'kill $(jobs -p)' EXIT

amixer set PCM -- 57%
mpg123 /home/mgeorg/wakeup/data/alarm.mp3
amixer set PCM -- 50%
# sleep 2
# (echo "on 3000" >> /tmp/switch_command.fifo) &
sleep 5
date +"It is %R on %B \
$(python /home/mgeorg/wakeup/ordinal.py $(date +"%d"))" | festival --tts
sleep 300
echo "5 minutes have passed.  Time to get up." | festival --tts
sleep 180
echo "8 minutes have passed." | festival --tts
sleep 180
echo "11 minutes." | festival --tts
sleep 120
echo "13 minutes." | festival --tts
sleep 60
echo "14 minutes." | festival --tts
sleep 60
echo "15 minutes have passed.  You win, I give up on you." | festival --tts
sleep 120
# echo "Time to get up." | festival --tts
# sleep 120
# echo "Another 2 minutes of your life passed." | festival --tts
# sleep 120
# echo "I know you are tired, so am I." | festival --tts
# sleep 120
# echo "Sha-la-la-la my oh my." | festival --tts
# sleep 120
# echo "looks like the boy too shy." | festival --tts
# sleep 120
# echo "ain't gonna press the button." | festival --tts
# sleep 120
# echo "Sha-la-la-la my oh my." | festival --tts
# sleep 120
# echo "ain't that a shame." | festival --tts
# sleep 120
# echo "you're gonna miss the button." | festival --tts
# sleep 120
# echo "Just get up already." | festival --tts
# sleep 120
# echo "You really don't have an excuse." | festival --tts
# sleep 120
# echo "You are not playing on your phone are you?" | festival --tts
# sleep 120
# echo "Time will pass just the same if you press the button." | festival --tts
# sleep 120
# echo "I can do this all day." | festival --tts
# sleep 120
# echo "It really is time to get up." | festival --tts
# sleep 120
# echo "You best not be in the room, I'm going to get angry." | festival --tts
# sleep 120
# echo "Final warning." | festival --tts
# sleep 120
# echo "Ok, you win, I give up on you." | festival --tts
# sleep 120
# 
