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
import simple_pubsub
import morning

switch_on = False
button1_press_time = datetime.datetime.now()
button2_press_time = button1_press_time
off_timer = None
off_timer_time = None


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
  if last_press + datetime.timedelta(milliseconds=200) > now:
    print('button1: bounced button press ignored.')
    return
  time.sleep(0.01)  # Wait 10ms for transients to disappear.
  if (GPIO.input(button1_pin) != GPIO.LOW):
    print('button1: transient detected.')
    # Reset press time to previous press time.
    button1_press_time = last_press
    return
  print('button1: Pressed')
  if switch_on and last_press + datetime.timedelta(seconds=1) > now:
    return IncreaseOnTime(15*60)
  if switch_on:
    return SwitchOffAndCancelTimer()
  return SwitchOn(15*60)  # 15 min


def Button2Pressed(channel):
  global button2_press_time
  global notify_button2_pressed
  last_press = button2_press_time
  now = datetime.datetime.now()
  button2_press_time = now
  if last_press + datetime.timedelta(milliseconds=300) > now:
    print('button2: bounced button press ignored.')
    return
  time.sleep(0.01)  # Wait 10ms for transients to disappear.
  if (GPIO.input(button2_pin) != GPIO.LOW):
    print('button2: transient detected.')
    # Reset press time to previous press time.
    button2_press_time = last_press
    return
  print('button2: Pressed')
  if notify_button2_pressed:
    print('Notifying service rather than normal behavior.')
    notify_button2_pressed()
    notify_button2_pressed = None
    return
  time.sleep(1)  # Wait for long press.
  if (GPIO.input(button2_pin) != GPIO.LOW):
    print('button2: short press.')
    festival_thread = threading.Thread(target=FestivalNextWakeupTime)
    festival_thread.start()
    button2_press_time = datetime.datetime.now()
    return
  print('button2: long press.')
  morn = morning.Morning()
  timer = morn.GetNextTimer()
  wakeup_date_key = timer.WakeupDate()
  try:
    delay = 0
    delay_date_key = None
    with open('/home/mgeorg/wakeup/data/delay.txt', 'r') as f:
      m = re.match(r'\s*(\d{4}-\d{2}-\d{2})\s+(\d+)', f.read())
      if not m:
        raise ValueError('delay.txt did not contain right values.')
      delay_date_key = m.group(1)
      delay = int(m.group(2))
  except:
    delay_date_key = None
    delay = 0
  if delay_date_key != wakeup_date_key:
    delay = 0
  try:
    with open('/home/mgeorg/wakeup/data/delay.txt', 'w') as f:
      f.write('{} {}\n'.format(wakeup_date_key, delay+15))
  except:
    pass
  delay_timedelta = datetime.timedelta(minutes=delay+15)
  delay_hours = (delay+15) / 60
  delay_minutes = (delay+15) % 60
  if delay_hours > 0:
    hour_plural = ''
    if delay_hours > 1:
      hour_plural = 's'
    delay_string = 'Delay increased to {} hour{} and {} minutes.'.format(
        delay_hours, hour_plural, delay_minutes)
  else:
    delay_string = 'Delay increased to {} minutes.'.format(
        delay_minutes)
  print(delay_string)

  festival_thread = threading.Thread(target=RunFestival, args=(delay_string,))
  festival_thread.start()
  # Set button press time as the time at which we're returning from
  # the function.  There may be invocations of the function triggered
  # by transients that are waiting to execute.
  button2_press_time = datetime.datetime.now()


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
  global off_timer_time
  CancelTimer()
  print('Turning on')
  switch_on = True
  GPIO.output(switch_pin, GPIO.HIGH)
  off_timer_time = num_sec
  off_timer = threading.Timer(off_timer_time, SwitchOff)
  off_timer.start()


def IncreaseOnTime(num_sec):
  global switch_on
  global off_timer_time
  print('Increasing time on')
  if not switch_on:
    print('Switch is not on')
    return
  new_time = off_timer_time + num_sec
  SwitchOn(new_time)
  festival_thread = threading.Thread(
      target=RunFestival, args=('{} minutes.'.format(new_time/60),))
  festival_thread.start()


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


def SigHandler(signum, frame):
  raise KeyboardInterrupt('signal %d received' % signum)


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
# PUD_OFF leaves the value floating.
# PUD_UP leaves it connected to high voltage with a resister.
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

GPIO.add_event_detect(button1_pin, GPIO.FALLING, Button1Pressed)
GPIO.add_event_detect(button2_pin, GPIO.FALLING, Button2Pressed)

GPIO.output(switch_pin, GPIO.LOW)

signal.signal(signal.SIGABRT, SigHandler)
signal.signal(signal.SIGALRM, SigHandler)
signal.signal(signal.SIGHUP, SigHandler)
signal.signal(signal.SIGQUIT, SigHandler)
signal.signal(signal.SIGTERM, SigHandler)
try:
  ControlLoop()
finally:
  Quit()
