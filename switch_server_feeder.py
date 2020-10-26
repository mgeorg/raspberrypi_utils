#!/usr/bin/python

import datetime
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time

import RPi.GPIO as GPIO

global network_down_times
global last_network_reset_time
network_down_times = []
last_network_reset_time = (
    datetime.datetime.now() - datetime.timedelta(minutes=60))

global last_feeder_start
global last_feeder_stop
last_feeder_start = None
last_feeder_stop = None

skip_feeding_file = '/home/mgeorg/wakeup/data/skip_feeding.txt'

def CheckPid(pid):
  """ Check For the existence of a unix pid. """
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  else:
    return True


try:
  with open('/tmp/switch_server_feeder_pid.txt', 'r') as f:
    pid = ''
    for line in f.read().splitlines():
      if line.strip():
        pid = line.strip()
        break
    if pid and CheckPid(int(pid)):
      print('switch_server_feeder is already running, exiting.')
      sys.exit(0)
except IOError:
  print('Can not read pid file.  Continuing...')

with open('/tmp/switch_server_feeder_pid.txt', 'w+') as f:
  f.write(str(os.getpid()))
  f.write('\n')

logging.basicConfig(filename='/home/mgeorg/feeder_log.txt',
                    format='%(asctime)s %(message)s',
                    level=logging.INFO)
logging.info('Starting up.')

def FileTouched(file_name, delete=False):
  try:
    with open(file_name, 'r') as f:
      data = f.read().strip()
    if delete:
      os.remove(file_name)
    return True
  except IOError:
    return False


def GetNetworkLogger(name, log_file, level=logging.INFO):
  formatter = logging.Formatter('%(asctime)s %(message)s')
  handler = logging.FileHandler(log_file)
  handler.setFormatter(formatter)
  logger = logging.getLogger(name)
  logger.setLevel(level)
  logger.addHandler(handler)
  return logger


def FeederChange(channel):
  global last_feeder_start
  global last_feeder_stop
  now = datetime.datetime.now()
  if (last_feeder_start is None or
      last_feeder_start < (now - datetime.timedelta(seconds=30))):
    print('resetting from {} to {}'.format(last_feeder_start, now))
    last_feeder_start = now
  last_feeder_stop = now
  print('feeder start {}, stop {}, diff {}'.format(
            last_feeder_start, last_feeder_stop,
            last_feeder_stop-last_feeder_start))


global network_log_file
network_log_file = '/home/mgeorg/network_log.txt'
global network_logger
network_logger = GetNetworkLogger('network_logger', network_log_file)
network_logger.info('Starting up.')


GPIO.setmode(GPIO.BCM)
feeder_pin = 27  # Broadcom pin 27 (PI pin 13)
# Connect feeder pin to relay controller
# (along with 3.3v (pin 1) and ground (pin 6)).
# Make sure you're using a 3v relay, the 5v relays look like they
# work but flake out randomly over time.
GPIO.setup(feeder_pin, GPIO.OUT)

feeder_activated_pin = 26 # Broadcom pin 26 (PI pin 37)
GPIO.setup(feeder_activated_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(feeder_activated_pin, GPIO.BOTH, callback=FeederChange)

modem_pin = 3 # Broadcom pin 03 (PI pin 5)
# Connect modem_pin and ground to modem relay switch.
GPIO.setup(modem_pin, GPIO.OUT)

# LOW is off on the feeder relay.
GPIO.output(feeder_pin, GPIO.LOW)
# LOW is off on the modem relay.
GPIO.output(modem_pin, GPIO.LOW)

def Quit():
  global network_logger
  print('Cleaning up GPIO')
  logging.info('Cleaning up GPIO.')
  GPIO.cleanup()
  logging.info('Quitting.')
  network_logger.info('Quitting.')


def SendMail(subject, content):
  start_time = datetime.datetime.now()
  print('Sending email:\nsubject: {}\n'.format(subject))
  logging.info('Sending email with subject: {}'.format(subject))
  p = subprocess.Popen(['msmtpq', 'manfred.georg@gmail.com'],
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  # This will timeout after a few seconds if there is no network connection.
  p.communicate(
"""From: Scarfie's Feeder <manfred.georg.automated@gmail.com>
Subject: {}

{}

---
Message creation time: {}
""".format(subject, content, str(datetime.datetime.now())))
  logging.info('Finished sending/enqueuing, returncode = %d.' % p.returncode)

def RoundTimeDelta(time_delta=None, round_to=datetime.timedelta(seconds=1)):
   """Round a datetime.timedelta object to some number of seconds.
   time_delta : datetime.timedelta object
   rount_to : datetime.timedelta round to this interval
   """
   if time_delta is None : return None
   microseconds = (time_delta.microseconds +
                   (time_delta.seconds + time_delta.days * 24 * 3600) * 10**6)
   round_to_microseconds = (round_to.microseconds +
                   (round_to.seconds + round_to.days * 24 * 3600) * 10**6)
   rounded_microseconds = (
       (microseconds + round_to_microseconds/2) // round_to_microseconds
       ) * round_to_microseconds
   return datetime.timedelta(microseconds=rounded_microseconds)

# # Feed without detecting how long the feeder was on for.
# def Feed(num_sec, extra=None):
#   logging.info('Feeding.')
#   print('Feeding')
#   # Feeder relay turns on when control is powered.
#   GPIO.output(feeder_pin, GPIO.HIGH)
#   time.sleep(num_sec)
#   GPIO.output(feeder_pin, GPIO.LOW)
#   time.sleep(1)
#   if extra:
#     subject_message = 'Feeding concluded (Extra)'
#     message = 'Extra feeding concluded'
#   else:
#     subject_message = 'Feeding concluded'
#     message = 'Feeding concluded'
#   SendMail('{} {}sec'.format(subject_message, num_sec),
#            '{} {}sec'.format(message, num_sec))

def FeedWithTimeDetection(num_sec, extra=None):
  global last_feeder_start
  global last_feeder_stop
  last_feeder_start = None
  last_feeder_stop = None
  logging.info('Feeding.')
  print('Feeding')
  # Feeder relay turns on when control is powered.
  GPIO.output(feeder_pin, GPIO.HIGH)
  time.sleep(num_sec)
  GPIO.output(feeder_pin, GPIO.LOW)
  time.sleep(1)
  succeeded = False
  time_fed = datetime.timedelta(seconds=0)
  if last_feeder_start is not None and last_feeder_stop is not None:
    time_fed = last_feeder_stop - last_feeder_start
    succeeded = True
  num_sec_fed = RoundTimeDelta(
      time_fed, datetime.timedelta(seconds=1)).total_seconds()
  print('measuring: feeder start {}, stop {}, time_fed {} ({}sec)'.format(
            last_feeder_start, last_feeder_stop,
            time_fed, num_sec_fed))
  if succeeded:
    if extra:
      subject_message = 'Feeding Extra'
      message = 'Extra feeding succeeded'
    else:
      subject_message = 'Feeding'
      message = 'Feeding succeeded'
    SendMail('{} {}sec ({})'.format(subject_message, num_sec, time_fed),
             '{} (meant for {}sec, got {}).'.format(
                 message, num_sec, time_fed))
  else:
    SendMail('FEEDING FAILED!!!',
             'FEEDING FAILED, meant for {} but got {}.'.format(
                 num_sec, time_fed))


def NetworkIsDown():
  global last_network_reset_time
  global network_down_times
  global network_logger
  print('Network is down.')
  logging.info('Network is down.')
  network_logger.info('Network is down.')
  now_time = datetime.datetime.now()
  network_down_times.append(now_time)
  pruned_times = []
  for reset_time in network_down_times:
    if now_time - reset_time < datetime.timedelta(minutes=5, seconds=30):
      pruned_times.append(reset_time)
  network_down_times = pruned_times
  if (len(network_down_times) >= 3 and
      now_time - last_network_reset_time >
          datetime.timedelta(minutes=15, seconds=30)):
    # Three network failures in the last 5.5 minutes and no reset
    # in the last 15.5 minutes.
    last_network_reset_time = now_time
    Modem(10)


def NetworkIsUp():
  global last_network_reset_time
  global network_down_times
  global network_logger
  if network_down_times:
    network_down_times = []
    print('Network is back up.')
    logging.info('Network is back up.')
    network_logger.info('Network is back up.')


def Modem(num_sec):
  global network_logger
  print('Resetting modem.')
  logging.info('Resetting modem.')
  network_logger.info('Resetting modem.')
  # Modem relay turns on when control is powered.
  GPIO.output(modem_pin, GPIO.HIGH)
  time.sleep(num_sec)
  GPIO.output(modem_pin, GPIO.LOW)
  print('Power restored to modem.')
  logging.info('Power restored to modem.')
  network_logger.info('Power restored to modem.')
  # There will be no network at this point.
  with open(network_log_file, 'r') as f:
    network_log_lines = f.read().splitlines()
  if len(network_log_lines) > 100:
    network_logs = '<truncated>...\n' + '\n'.join(network_log_lines[-100:])
  else:
    network_logs = '\n'.join(network_log_lines)
  SendMail('Modem Power-Cycled',
           'The Modem was power cycled at {}.\n\nNetwork logs:\n{}'.format(
               str(datetime.datetime.now()), network_logs))


def ControlLoop():
  global off_timer
  fifo_path = '/tmp/feeder_command.fifo'
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
      m = re.match(r'feed\s+(extra\s+)?(\d+)?$', data)
      if m:
        num_sec = 5  # Default feeder on time.
        if m.group(1):
          extra = True
        else:
          extra = False
        if m.group(2):
          num_sec = int(m.group(2).strip())
        if FileTouched(skip_feeding_file, True):
          print('skipped feeding {}sec'.format(num_sec))
          SendMail('FEEDING SKIPPED!!!',
                   'FEEDING SKIPPED, would have been {}sec.'.format(num_sec))
        else:
          FeedWithTimeDetection(num_sec, extra)
        continue
      m = re.match(r'cycle(?:\s+(\d+))?$', data)
      if m:
        num_sec = 10  # Default seconds to reset cable modem.
        if m.group(1):
          num_sec = int(m.group(1).strip())
        Modem(num_sec)
        continue
      m = re.match(r'network_is_down$', data)
      if m:
        NetworkIsDown()
        continue
      m = re.match(r'network_is_up$', data)
      if m:
        NetworkIsUp()
        continue
      print('Unable to understand "%s"' % (data))

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
