#!/usr/bin/python
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
  service_connection = rpyc.connect("localhost", 18861)
  service_connection.root.wait_for_button()
  button_pressed = True
  nag_alarm_process.terminate()
  # Turn on light.
  with open('/tmp/switch_command.fifo', 'w') as f:
    f.write('on 3000')
  # Start meditation session
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
