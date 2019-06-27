#!/usr/bin/python

import datetime
import subprocess
import re
import os
import sys

# From current directory
import next_sunrise

def CheckPid(pid):
  """ Check For the existence of a unix pid. """
  try:
    os.kill(pid, 0)
  except OSError:
    return False
  else:
    return True

class Morning(object):
  def __init__(self):
    self.day_to_number = {
      'monday'    : 0,
      'tuesday'   : 1,
      'wednesday' : 2,
      'thursday'  : 3,
      'friday'    : 4,
      'saturday'  : 5,
      'sunday'    : 6,
      'holiday'   : 7,
      'blacklist' : 8,
      }
    self.InitializeBlacklist()

  def InitializeBlacklist(self):
    self.anchor = None
    self.day_wakeups = [None] * len(self.day_to_number)
    self.scripts = set()
    self.blacklist = dict()
    self.delay = 0
    try:
      with open('/home/mgeorg/wakeup/data/delay.txt', 'r') as f:
        m = re.match(r'\s*(\d{4})-(\d{2})-(\d{2})\s+(-?\d+)', f.read())
        if not m:
          raise ValueError('delay.txt did not contain right values.')
        self.delay_date = datetime.date(
            year=int(m.group(1)), month=int(m.group(2)), day=int(m.group(3)))
        self.delay = int(m.group(4))
    except:
      self.delay_date = None
      self.delay = 0
    with open('/home/mgeorg/wakeup/data/wakeup_times.txt', 'r') as f:
      for line in f.read().splitlines():
        line = line.strip()
        if line:
          m = re.match(
              r'^[aA]nchor\s+'
              r'(\d{4}-\d{2}-\d{2}'
              r'\s+[-+]?\d{1,2}:\d{2}\s+'
              r'[+]?\d{1,2}:\d{2})\s+'
              r'(\d{4}-\d{2}-\d{2}'
              r'\s+[-+]?\d{1,2}:\d{2}\s+'
              r'[+]?\d{1,2}:\d{2})',
              line)
          if m:
            # Matched the anchor line.
            self.anchor = next_sunrise.AnchorTime(m.group(1), m.group(2))
          # Match a day directive.
#           m = re.match(
#               r'^([mM]onday?|[tT]uesday|[wW]ednesday|[tT]hursday|'
#               r'[fF]riday|[sS]aturday|[sS]unday|[hH]oliday|[bB]lacklist)'
#               r'\s+([-+]?\d{1,2}:\d{2})\s+(\d{1,2}:\d{2})\s+(\S+\.sh)\s*$',
#               line)
          m = re.match(
              r'^([mM]onday|[tT]uesday|[wW]ednesday|[tT]hursday|'
              r'[fF]riday|[sS]aturday|[sS]unday|[hH]oliday|[bB]lacklist)'
              r'\s+([aA]nchor)?([-+]?\d{1,2}:\d{2})\s+(\S+\.sh)\s*$',
              line)
          if m:
            day = self.day_to_number[m.group(1).lower()]
            if m.group(2):
              self.day_wakeups[day] = (
                  next_sunrise.ParseTimeOffset(m.group(3)),
                  True,
                  m.group(4))
            else:
              self.day_wakeups[day] = (
                  next_sunrise.ParseTimeInDay(m.group(3)),
                  False,
                  m.group(4))
            self.scripts.add(m.group(4))
            continue
          m = re.match(r'^(\d{4}-\d{2}-\d{2})(?:\s+([^#]*))?.*$', line)
          if m:
            directive = ''
            if m.group(2) and m.group(2).strip():
              directive = m.group(2).strip()
            self.blacklist[m.group(1)] = directive
    for day_wakeup in self.day_wakeups:
      assert day_wakeup
    assert self.anchor

  def GetTimer(self, current_time):
    date_key = '%04d-%02d-%02d' % (current_time.year,
                                   current_time.month,
                                   current_time.day)
    delay = 0
    if self.delay_date:
      delay_date_key = '%04d-%02d-%02d' % (
          self.delay_date.year,
          self.delay_date.month,
          self.delay_date.day)
      if delay_date_key == date_key:
        delay = self.delay

    if date_key in self.blacklist:
      directive = self.blacklist[date_key]
      print('Date is in blacklist file (date %s) with directive "%s".' % (
                date_key, directive))
      m = re.match(r'^\s*(?:([aA]nchor)?([-+]?\d{1,2}:\d{2}))?\s*'
                   r'([^#]*)?.*$', directive)
      if m:
        sunrise_offset, from_anchor, script = self.day_wakeups[
            self.day_to_number['blacklist']]
        do_wakeup = False
        if m.group(2):
          from_anchor = bool(m.group(1))
          sunrise_offset = m.group(2)
          do_wakeup = True
          if from_anchor:
            print('Using provided offset from anchor: %s' % sunrise_offset)
          else:
            print('Using provided time: %s' % sunrise_offset)
        if m.group(3) and m.group(3).strip().lower() in self.scripts:
          script = m.group(3).strip().lower()
          do_wakeup = True
        if do_wakeup:
          print('Using script %s' % script)
          timer = next_sunrise.WakeupTimer(self.anchor, date_key,
                                           sunrise_offset, from_anchor,
                                           delay, script)
        else:
          print('Skipping blacklisted date.')
          timer = None
      else:
        print('Skipping blacklisted date.')
        timer = None
    else:
      day = current_time.weekday()
      sunrise_offset, from_anchor, script = self.day_wakeups[day]
      timer = next_sunrise.WakeupTimer(self.anchor, date_key, sunrise_offset,
                                       from_anchor, delay, script)
    return timer

  def GetNextTimer(self):
    current_time = datetime.datetime.now()
    timer_time = current_time
    timer = self.GetTimer(current_time)
    if not timer or timer.WakeupTime() < current_time:
      # print('It is after wakeup today.')
      timer_time = current_time + datetime.timedelta(days=1)
      timer = self.GetTimer(timer_time)
    while not timer and timer_time < current_time + datetime.timedelta(days=30):
      timer_time = timer_time + datetime.timedelta(days=1)
      timer = self.GetTimer(timer_time)
    return timer

if __name__ == "__main__":
  try:
    with open('/tmp/wakeup_pid.txt', 'r') as f:
      pid = ''
      for line in f.read().splitlines():
        if line.strip():
          pid = line.strip()
          break
      if pid and CheckPid(int(pid)):
        print('wakeup is already running, exiting.')
        sys.exit(0)
  except IOError:
    print('Can not read pid file.  Continuing...')

  with open('/tmp/wakeup_pid.txt', 'w') as f:
    f.write(str(os.getpid()))
    f.write('\n')

  morning = Morning()

  timer = morning.GetNextTimer()
  if not timer:
    sys.exit(1)

  timer.Print()
  print(timer.Message())

  print('Waiting for wakeup time.')
  if not timer.WaitUntilWakeup(datetime.timedelta(minutes=10)):
    # Early termination is not an error.
    sys.exit(0)

  try:
    with open('/home/mgeorg/wakeup/data/delay.txt', 'w') as f:
      f.write('')
  except:
    pass

  print('Running script "%s".' % timer.script)
  subprocess.check_call(['/bin/bash',
                         '/home/mgeorg/wakeup/scripts/%s' % timer.script])

  os.unlink('/tmp/wakeup_pid.txt')


