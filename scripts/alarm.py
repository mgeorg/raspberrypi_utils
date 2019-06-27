#!/usr/bin/python
import datetime
import subprocess
import sys
import threading
import time

import simple_pubsub

# import ordinal
global nag_alarm_process
global button_pressed
nag_alarm_process = None
button_pressed = False

def SecondPart():
  global nag_alarm_process
  global button_pressed

  with open('/tmp/switch_command.fifo', 'w') as f:
    f.write('ignore_delay 3600')  # Ignore buttons for 1 hour.

  pubsub = simple_pubsub.SimplePubSub('/home/mgeorg/button_press.pubsub')
  # Wait for button press.
  print('Waiting for button press.')
  button_pressed = False
  event = None
  while event is None or (event[2] != 'button2' and event[2] != 'button3'):
    event = pubsub.Poll()
    if event is None:
      time.sleep(0.1)

  button_pressed = True

  nag_alarm_process.terminate()
  # Turn on light.
  with open('/tmp/switch_command.fifo', 'w') as f:
    f.write('on 3000')  # 50 minutes

  # If the button is pressed again within 3 seconds, then we turn
  # off the light and go back to bed.
  deadline = datetime.datetime.now() + datetime.timedelta(seconds=3)
  event = None
  while event is None or (event[2] != 'button2' and event[2] != 'button3'):
    if datetime.datetime.now() > deadline:
      break
    event = pubsub.Poll()
    if event is None:
      time.sleep(0.1)

  # Stop ignoring button presses.
  with open('/tmp/switch_command.fifo', 'w') as f:
    f.write('ignore_delay 0')

  if event and (event[2] == 'button2' or event[2] == 'button3'):
    # Button was pressed, go back to bed.
    with open('/tmp/switch_command.fifo', 'w') as f:
      f.write('off')
    return

  # Start meditation session
  print('Starting meditation session.')
  meditation_process = subprocess.Popen(
      ['/home/mgeorg/wakeup/scripts/meditation_session.sh', '10', '0'])
  meditation_process.communicate()
  print('meditation_process.sh returned %d' % meditation_process.returncode)

# Create a thread which runs the second part.
second_part_thread = threading.Thread(target=SecondPart)
second_part_thread.daemon = True
second_part_thread.start()

# Set volume
nag_alarm_process = subprocess.Popen(
    ['/home/mgeorg/wakeup/scripts/nag_alarm.sh'])
nag_alarm_process.wait()
print('nag_alarm.sh returned %d' % nag_alarm_process.returncode)

if button_pressed:
  print('waiting for second part to finish')
  second_part_thread.join()
else:
  # Just exit process
  print('Just exiting the process')
