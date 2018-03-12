#!/usr/bin/python

import datetime
import os
import re
import signal
import subprocess
import sys
import threading
import time

import RPi.GPIO as GPIO

# From current directory
import morning

switch_on = False
button1_press_time = datetime.datetime.now()
button2_press_time = button1_press_time
off_timer = None


def CheckPid(pid):
  """ Check For the existence of a unix pid. """
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  else:
    return True


def Button1Pressed(channel):
  global button1_press_time
  last_press = button1_press_time
  now = datetime.datetime.now()
  button1_press_time = now
  if last_press + datetime.timedelta(milliseconds=300) > now:
    print('button1: bounced button press ignored.')
    return
  time.sleep(0.05)  # Wait 50ms for transients to disappear.
  if (GPIO.input(button1_pin) != GPIO.LOW):
    print('button1: transient detected.')
    # Reset press time to previous press time.
    button1_press_time = last_press
    return
  print('button1: Pressed')
  if switch_on:
    SwitchOffAndCancelTimer()
  else:
    SwitchOn(15*60)  # 15 min
    time.sleep(1)  # Wait for long press.
    if (GPIO.input(button1_pin) != GPIO.LOW):
      print('button1: short press.')
      return
    print('button1: long press.')
    SwitchOn(45*60)  # 45 min
    festival_thread = threading.Thread(
        target=RunFestival, args=('45 minutes.',))
    festival_thread.start()


def Button2Pressed(channel):
  global button2_press_time
  last_press = button2_press_time
  now = datetime.datetime.now()
  button2_press_time = now
  if last_press + datetime.timedelta(milliseconds=300) > now:
    print('button2: bounced button press ignored.')
    return
  time.sleep(0.05)  # Wait 50ms for transients to disappear.
  if (GPIO.input(button2_pin) != GPIO.LOW):
    print('button2: transient detected.')
    # Reset press time to previous press time.
    button2_press_time = last_press
    return
  print('button2: Pressed')
  festival_thread = threading.Thread(target=FestivalNextWakeupTime)
  festival_thread.start()
  time.sleep(1)  # Wait for long press.
  if (GPIO.input(button2_pin) != GPIO.LOW):
    print('button2: short press.')
    return
  print('button2: long press.')


def FestivalNextWakeupTime():
  # Reload every time (needs to load blacklist).
  morn = morning.Morning()
  timer = morn.GetNextTimer()
  message = 'No wakeup in the next 30 days'
  if timer:
    message = timer.Message()
  RunFestival(message)


def RunFestival(message):
  p = subprocess.Popen(['/usr/bin/festival', '--tts'], stdin=subprocess.PIPE)
  p.communicate(message)
  print('festival returned %d' % p.returncode)


try:
  with open('/tmp/switch_server_pid.txt', 'r') as f:
    pid = ''
    for line in f.read().splitlines():
      if line.strip():
        pid = line.strip()
        break
    if pid and CheckPid(int(pid)):
      print('switch_server is already running, exiting.')
      sys.exit(0)
except IOError:
  print('Can not read pid file.  Continuing...')

with open('/tmp/switch_server_pid.txt', 'w') as f:
  f.write(str(os.getpid()))
  f.write('\n')

GPIO.setmode(GPIO.BCM)
switch_pin = 18 # Broadcom pin 18 (PI pin 12)
# Connect switch_pin and ground (pin 14) to relay switch.
button1_pin = 23 # Broadcom pin 23 (PI pin 16)
button2_pin = 24 # Broadcom pin 24 (PI pin 18)
# Connect button pins to 3.3v power (pin 1 or 17) each with a 10kOhm Resister.
# Connect button pins to ground each with a 100nF capacitor.

GPIO.setup(switch_pin, GPIO.OUT)
# GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

GPIO.add_event_detect(button1_pin, GPIO.FALLING, Button1Pressed)
GPIO.add_event_detect(button2_pin, GPIO.FALLING, Button2Pressed)

GPIO.output(switch_pin, GPIO.LOW)

def CancelTimer():
  global off_timer
  if off_timer is not None:
    print('Cancelling timer')
    off_timer.cancel()
    off_timer.join()
    off_timer = None

def Quit():
  CancelTimer()
  print('Cleaning up GPIO')
  GPIO.cleanup()

def SwitchOffAndCancelTimer():
  CancelTimer()
  SwitchOff()

def SwitchOff():
  global switch_on
  print('Turning off')
  switch_on = False
  GPIO.output(switch_pin, GPIO.LOW)

def SwitchOn(num_sec):
  global switch_on
  global off_timer
  CancelTimer()
  print('Turning on')
  switch_on = True
  GPIO.output(switch_pin, GPIO.HIGH)
  off_timer = threading.Timer(num_sec, SwitchOff)
  off_timer.start()

def ControlLoop():
  global off_timer
  fifo_path = '/tmp/switch_command.fifo'
  if os.path.exists(fifo_path):
    os.unlink(fifo_path)
  os.mkfifo(fifo_path)
  print('Created fifo: ' + fifo_path)
  while True:
    with open(fifo_path, 'r') as f:
      data = f.read().strip()
      m = re.match(r'quit(?:\s.*)?$', data)
      if m:
        break
      m = re.match(r'print (\S+.*?)\s*$', data)
      if m:
        print('"' + m.group(1) + '"')
        continue
      m = re.match(r'on(?:\s+(\d+))?$', data)
      if m:
        num_sec = 60*45  # 45 minutes.
        if m.group(1):
          num_sec = int(m.group(1).strip())
        SwitchOn(num_sec)
        continue
      m = re.match(r'off(?:\s.*)?$', data)
      if m:
        SwitchOffAndCancelTimer()
        continue
      print('Unable to understand "%s"' % (data))

# control_loop_thread = threading.Thread(target=ControlLoop)
# control_loop_thread.daemon = True
# control_loop_thread.start()
# control_loop_thread.join()

def SigHandler(signum, frame):
  raise KeyboardInterrupt('signal %d received' % signum)

signal.signal(signal.SIGABRT, SigHandler)
signal.signal(signal.SIGALRM, SigHandler)
signal.signal(signal.SIGHUP, SigHandler)
signal.signal(signal.SIGQUIT, SigHandler)
signal.signal(signal.SIGTERM, SigHandler)
try:
  ControlLoop()
finally:
  Quit()
