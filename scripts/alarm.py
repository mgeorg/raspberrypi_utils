#!/usr/bin/python
import datetime
import rpyc
import subprocess
import sys
import threading
import time

# import ordinal
global nag_alarm_process
global button_pressed
nag_alarm_process = None
button_pressed = False

def SecondPart():
  global nag_alarm_process
  global button_pressed
  # Wait for button press.
  print('Waiting for button press.')
  service_connection = rpyc.connect("localhost", 18861)
  button_pressed = service_connection.root.wait_for_button()
  nag_alarm_process.terminate()
  assert button_pressed
  # Turn on light.
  with open('/tmp/switch_command.fifo', 'w') as f:
    f.write('on 3000')

  # Wait a few seconds for a second button press.
  print('Waiting for secondary button press.')
  button_pressed = service_connection.root.wait_for_button(timeout_ms=3000)
  if button_pressed:
    with open('/tmp/switch_command.fifo', 'w') as f:
      f.write('off')
    return

  # Start meditation session
  print('Starting meditation session.')
  meditation_process = subprocess.Popen(
      ['/home/mgeorg/wakeup/scripts/meditation_session.sh', '35', '10'])
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
