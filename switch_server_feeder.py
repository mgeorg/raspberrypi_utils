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

global mailer_threads
global network_down_times
global last_network_reset_time
mailer_threads = []
network_down_times = []
last_network_reset_time = (
    datetime.datetime.now() - datetime.timedelta(minutes=60))


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

GPIO.setmode(GPIO.BCM)
feeder_pin = 2  # Broadcom pin 02 (PI pin 3)
# Connect feeder pin to relay controller
# (along with 3.3v (pin 1) and ground (pin 6)).
modem_pin = 3 # Broadcom pin 03 (PI pin 5)
# Connect modem_pin and ground to modem relay switch.
GPIO.setup(feeder_pin, GPIO.OUT)
GPIO.setup(modem_pin, GPIO.OUT)

# HIGH is off on the feeder relay.
GPIO.output(feeder_pin, GPIO.HIGH)
# LOW is off on the modem relay.
GPIO.output(modem_pin, GPIO.LOW)

def Quit():
  global mailer_threads
  for t in mailer_threads:
    if isinstance(t, threading._Timer):
      print('cancelling timer')
      t.cancel()
    t.join()
  mailer_threads = []
  print('Cleaning up GPIO')
  logging.info('Cleaning up GPIO.')
  GPIO.cleanup()
  logging.info('Quitting.')


def SendMail(subject, content, timeout=None):
  start_time = datetime.datetime.now()
  print('Sending email:\nsubject: %s\nbody:\n%s' % (subject, content))
  logging.info('Sending email:\nsubject: %s\nbody:\n%s' % (subject, content))
  p = subprocess.Popen(['msmtpq', 'manfred.georg@gmail.com'],
      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
      '-s', subject,
      '-r', 
  p.communicate(
"""From: Scarfie's Feeder <manfred.georg.automated@gmail.com>
Subject: {}

{}

---
Message creation time: {}
""".format(subject, content, str(datetime.datetime.now())))
  p.stdin.close()
  p.poll()
  while (p.returncode is None and
         timeout is not None and
         datetime.datetime.now() < start_time + timeout):
    p.poll()
    time.sleep(.01)
  if p.returncode is None:
    print('Process hung, terminating it.')
    p.terminate()
    p.wait()
    print('Writing message to file.')
    with open('/home/mgeorg/switch_unsent_mail.txt', 'a+') as f:
      f.write('Subject: ' + subject)
      f.write('\nContent: ' + content)
      f.write('\nEnd')
  mail_stdout = p.stdout.read()
  mail_stderr = p.stderr.read()
  print('Finished sending.')
  logging.info('Finished sending %d.' % p.returncode)


def Feed(num_sec):
  logging.info('Feeding.')
  print('Feeding')
  # Feeder relay turns on when control is grounded.
  GPIO.output(feeder_pin, GPIO.LOW)
  time.sleep(num_sec)
  GPIO.output(feeder_pin, GPIO.HIGH)
  mailer_threads.append(
      threading.Thread(
          target=SendMail,
          args=('Feeding',
                'Feeding succeeded.\n\n' + str(datetime.datetime.now()),
                datetime.timedelta(seconds=10))))
  mailer_threads[-1].start()
  # TODO(mgeorg) Remove from list after it runs.


def NetworkIsDown():
  global last_network_reset_time
  global network_down_times
  print('Recording that network is down.')
  logging.info('Recording that network is down.')
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


def Modem(num_sec):
  print('Resetting modem.')
  logging.info('Resetting modem.')
  # Modem relay turns on when control is grounded.
  GPIO.output(modem_pin, GPIO.HIGH)
  time.sleep(num_sec)
  GPIO.output(modem_pin, GPIO.LOW)
  print('Power restored to modem.')
  logging.info('Power restored to modem.')
  # TODO(mgeorg) There will be no network at this point.
  mailer_threads.append(
      threading.Timer(
          3,
          # 300,  # 5 min.
          function=SendMail,
          args=('Modem Power-Cycled',
                'The Modem was power cycled.\n\n' +
                str(datetime.datetime.now()),
                datetime.timedelta(seconds=10))))
  mailer_threads[-1].start()


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
      m = re.match(r'feed(?:\s+(\d+))?$', data)
      if m:
        num_sec = 5  # Default feeder on time.
        if m.group(1):
          num_sec = int(m.group(1).strip())
        Feed(num_sec)
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
