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
button2_press_time = datetime.datetime.now()
button3_press_time = datetime.datetime.now()
button4_press_time = datetime.datetime.now()
off_timer = None
off_timer_time = 0
schedule_delay_timer = None
off_time_increase_timer = None
meditation_timer = None
ignore_delay_until = datetime.datetime.now()
delay_buttons_set_meditation_time_until = datetime.datetime.now()
meditation_time = 0
pubsub_handle = simple_pubsub.SimplePubSub('/home/mgeorg/button_press.pubsub')
button_bounce_time = 100
scheduled_delay_increase = 0


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
  if last_press + datetime.timedelta(milliseconds=button_bounce_time) > now:
    print('button1: bounced button press ignored.')
    button1_press_time = last_press
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
  global ignore_delay_until
  global delay_buttons_set_meditation_time_until
  global meditation_time
  last_press = button2_press_time
  now = datetime.datetime.now()
  button2_press_time = now
  if last_press + datetime.timedelta(milliseconds=button_bounce_time) > now:
    print('button2: bounced button press ignored.')
    button2_press_time = last_press
    return
  time.sleep(0.01)  # Wait 10ms for transients to disappear.
  if (GPIO.input(button2_pin) != GPIO.LOW):
    print('button2: transient detected.')
    # Reset press time to previous press time.
    button2_press_time = last_press
    return
  print('button2: Pressed')
  pubsub_handle.Publish('switch_server', 'button2 pressed')

  if delay_buttons_set_meditation_time_until > now:
    meditation_time -= 5*60
    if meditation_time > 0:
      festival_thread = threading.Thread(
          target=RunFestival, args=('{} minutes.'.format(meditation_time/60),))
      festival_thread.start()
    else:
      meditation_time = 0
      festival_thread = threading.Thread(
          target=RunFestival, args=('no meditation set.',))
      festival_thread.start()
    return

  if ignore_delay_until > now:
    return

  ScheduleUpdateDelay(-15)


def Button3Pressed(channel):
  global button3_press_time
  global ignore_delay_until
  global delay_buttons_set_meditation_time_until
  global meditation_time
  last_press = button3_press_time
  now = datetime.datetime.now()
  button3_press_time = now
  if last_press + datetime.timedelta(milliseconds=button_bounce_time) > now:
    print('button3: bounced button press ignored.')
    button3_press_time = last_press
    return
  time.sleep(0.01)  # Wait 10ms for transients to disappear.
  if (GPIO.input(button3_pin) != GPIO.LOW):
    print('button3: transient detected.')
    # Reset press time to previous press time.
    button3_press_time = last_press
    return
  print('button3: Pressed')
  pubsub_handle.Publish('switch_server', 'button3 pressed')

  if delay_buttons_set_meditation_time_until > now:
    meditation_time += 5*60
    festival_thread = threading.Thread(
        target=RunFestival, args=('{} minutes.'.format(meditation_time/60),))
    festival_thread.start()
    return

  if ignore_delay_until > now:
    return

  ScheduleUpdateDelay(15)


def Button4Pressed(channel):
  global button4_press_time
  last_press = button4_press_time
  now = datetime.datetime.now()
  button4_press_time = now
  if last_press + datetime.timedelta(milliseconds=button_bounce_time) > now:
    print('button4: bounced button press ignored.')
    button4_press_time = last_press
    return
  time.sleep(0.01)  # Wait 10ms for transients to disappear.
  if (GPIO.input(button4_pin) != GPIO.LOW):
    print('button4: transient detected.')
    # Reset press time to previous press time.
    button4_press_time = last_press
    return
  print('button4: Pressed')

  DelayButtonsSetMeditationTime(60)
  meditation_timer = threading.Timer(60, StartMeditation)
  meditation_timer.start()


def DelayButtonsSetMeditationTime(num_sec):
  global delay_buttons_set_meditation_time_until
  print('Delay buttons will set meditation time for {} seconds.'.format(
      num_sec))
  delay_buttons_set_meditation_time_until = (
      datetime.datetime.now() + datetime.timedelta(seconds=num_sec))


def StartMeditation():
  global meditation_time
  if meditation_time <= 0:
    return
  meditation_time_minutes = meditation_time/60
  warn_time = 0
  if meditation_time_minutes >= 20:
    warn_time = 5
  if meditation_time_minutes >= 25:
    warn_time = 10
  meditation_process = subprocess.Popen(
        ['/home/mgeorg/wakeup/scripts/meditation_session.sh',
         str(meditation_time_minutes), str(warn_time)])
  meditation_process.communicate()
  print('meditation_process.sh returned %d' % meditation_process.returncode)


def ScheduleUpdateDelay(increase):
  global scheduled_delay_increase
  global schedule_delay_timer
  scheduled_delay_increase += increase

  CancelDelayIncreaseTimer()
  schedule_delay_timer = threading.Timer(1, UpdateDelay)
  schedule_delay_timer.start()


def UpdateDelay():
  global scheduled_delay_increase
  morn = morning.Morning()
  timer = morn.GetNextTimer()
  wakeup_date_key = timer.WakeupDate()
  try:
    delay = 0
    delay_date_key = None
    with open('/home/mgeorg/wakeup/data/delay.txt', 'r') as f:
      m = re.match(r'\s*(\d{4}-\d{2}-\d{2})\s+(-?\d+)', f.read())
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
      f.write('{} {}\n'.format(wakeup_date_key,
                               delay+scheduled_delay_increase))
  except:
    pass
  scheduled_delay_increase = 0
  AnnounceNextWakeupTime()


def CancelIncreaseTimer():
  global off_time_increase_timer
  if off_time_increase_timer is not None:
    print('Cancelling Increase timer')
    off_time_increase_timer.cancel()
    off_time_increase_timer.join()
    off_time_increase_timer = None


def CancelDelayIncreaseTimer():
  global schedule_delay_timer
  if schedule_delay_timer is not None:
    print('Cancelling Delay Increase timer')
    schedule_delay_timer.cancel()
    schedule_delay_timer.join()
    schedule_delay_timer = None


def AnnounceNextWakeupTime():
  festival_thread = threading.Thread(target=FestivalNextWakeupTime)
  festival_thread.start()


def AnnounceIncrease():
  global off_timer_time
  festival_thread = threading.Thread(
      target=RunFestival, args=('{} minutes.'.format(off_timer_time/60),))
  festival_thread.start()


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
  global off_time_increase_timer
  print('Increasing time on')
  if not switch_on:
    print('Switch is not on')
    return
  SwitchOn(off_timer_time + num_sec)

  CancelIncreaseTimer()
  off_time_increase_timer = threading.Timer(1, AnnounceIncrease)
  off_time_increase_timer.start()


def IgnoreDelay(num_sec):
  global ignore_delay_until
  print('Ignoring delay button presses for {} seconds.'.format(num_sec))
  ignore_delay_until = (
      datetime.datetime.now() + datetime.timedelta(seconds=num_sec))


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
      m = re.match(r'ignore_delay(?:\s+(\d+))?$', data)
      if m:
        num_sec = 60*1  # 1 minute.
        if m.group(1):
          num_sec = int(m.group(1).strip())
        IgnoreDelay(num_sec)
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
button3_pin = 25 # Broadcom pin 25 (PI pin 22)
button4_pin = 8  # Broadcom pin  8 (PI pin 24)
# Connect button pins to 3.3v power (pin 1 or 17) each with a 10kOhm Resister.
# Connect button pins to ground (pin 14 or 20) each with a 100nF capacitor.

GPIO.setup(switch_pin, GPIO.OUT)
# PUD_OFF leaves the value floating.
# PUD_UP leaves it connected to high voltage with a resister.
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.setup(button3_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.setup(button4_pin, GPIO.IN, pull_up_down=GPIO.PUD_OFF)

GPIO.add_event_detect(button1_pin, GPIO.FALLING, Button1Pressed)
GPIO.add_event_detect(button2_pin, GPIO.FALLING, Button2Pressed)
GPIO.add_event_detect(button3_pin, GPIO.FALLING, Button3Pressed)
GPIO.add_event_detect(button4_pin, GPIO.FALLING, Button4Pressed)

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
