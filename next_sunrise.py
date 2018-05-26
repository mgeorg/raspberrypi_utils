#!/usr/bin/python

import astral
import datetime
import time
import sys
import re

def ParseTimeInDay(data):
  m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', data)
  assert m
  return datetime.time(hour=int(m.group(1)), minute=int(m.group(2)))


def ParseDay(data):
  m = re.match(r'^\s*(\d{4})-(\d{2})-(\d{2})\s*$', data)
  assert m
  return datetime.date(year=int(m.group(1)), month=int(m.group(2)),
                       day=int(m.group(3)))


def ParseTimeOffset(data):
  m = re.match(r'^\s*([+-])?(\d{1,2}):(\d{2})\s*$', data)
  assert m
  if m.group(1) is None or m.group(1) == '+':
    sign = 1
  elif m.group(1) == '-':
    sign = -1
  else:
    assert False
  return datetime.timedelta(
      hours=sign*int(m.group(2)), minutes=sign*int(m.group(3)))


def GetSunriseTime(day):
  a = astral.Astral()
  a.solar_depression = 'civil'

  l = astral.Location()
  l.name = '9WGJ+42 Mountain View California'
  l.region = 'USA'
  l.latitude = 37.375313
  l.longitude = -122.069938
  l.timezone = 'US/Pacific'
  l.elevation = 42.865

  # Finding the next sunrise.
  sun = l.sun(day, local=True)

  return sun['sunrise']


class AnchorTime(object):
  def __init__(self, start_date_string, end_date_string=None):
    m = re.match(r'\s*(\d{4}-\d{2}-\d{2})'
                 r'\s+([-+]?\d{1,2}:\d{2})\s+'
                 r'[+]?(\d{1,2}:\d{2})\s*', start_date_string)
    assert m, start_date_string
    self.start_day = ParseDay(m.group(1))
    self.start_offset = ParseTimeOffset(m.group(2))
    self.start_max_wakeup = ParseTimeInDay(m.group(3))

    self.end_day = None
    self.end_offset = None
    self.end_max_wakeup = None

    if end_date_string:
      m = re.match(r'\s*(\d{4}-\d{2}-\d{2})'
                   r'\s+([-+]?\d{1,2}:\d{2})\s+'
                   r'[+]?(\d{1,2}:\d{2})\s*', end_date_string)
      assert m
      self.end_day = ParseDay(m.group(1))
      self.end_offset = ParseTimeOffset(m.group(2))
      self.end_max_wakeup = ParseTimeInDay(m.group(3))
      assert self.start_day <= self.end_day
    
  def GetOffsetAndMaxWakeup(self, day):
    if day <= self.start_day or self.end_day is None:
      return (self.start_offset, self.start_max_wakeup)
    if day >= self.end_day:
      return (self.end_offset, self.end_max_wakeup)
    interval = (self.end_day - self.start_day).days
    point_in_interval = (day - self.start_day).days
    offset = ((self.start_offset + self.end_offset)
              * interval / point_in_interval)
    start = datetime.datetime.combine(day, self.start_max_wakeup)
    end = datetime.datetime.combine(day, self.end_max_wakeup)
    max_wakeup = ((end - start) * point_in_interval / interval) + start
    assert max_wakeup.date() == day
    return (offset, max_wakeup.time())


class WakeupTimer(object):
  def __init__(self, anchor, date_string, offset_string, from_anchor,
               delay, script):
    self.anchor_offset = None
    self.anchor_max_wakeup = None
    self.sunrise_adjusted = None
    self.delay = delay
    self.script = script

    if isinstance(date_string, datetime.date):
      self.day = date_string
    else:
      self.day = ParseDay(date_string)
    self.sunrise  = GetSunriseTime(self.day).replace(tzinfo=None)

    print offset_string
    print from_anchor
    if isinstance(offset_string, datetime.timedelta):
      time_offset = offset_string
    elif isinstance(offset_string, datetime.time):
      time_offset = ParseTimeOffset('%02d:%02d' % (
          offset_string.hour, offset_string.minute))
    else:
      time_offset = ParseTimeOffset(offset_string)

    if from_anchor:
      self.anchor_offset, self.anchor_max_wakeup = (
          anchor.GetOffsetAndMaxWakeup(self.day))
      self.max_wakeup = datetime.datetime.combine(
          self.day, self.anchor_max_wakeup) + time_offset
      time_offset = self.anchor_offset + time_offset
      assert self.max_wakeup.date() == self.day, (
          'Adding the time offset shifted the wakeup to '
          'a different day %s + %s.' % (
          str(self.anchor_max_wakeup), str(time_offset)))
      self.sunrise_adjusted = self.sunrise + time_offset
      self.wakeup_time = min(self.sunrise_adjusted, self.max_wakeup)
    else:
      day_and_time = datetime.datetime(
          self.day.year, self.day.month, self.day.day)
      self.max_wakeup = day_and_time + time_offset
      self.wakeup_time = self.max_wakeup

  def Print(self):
    print('Sunrise:              %s' % str(self.sunrise))
    if self.anchor_offset:
      print('Anchor offset:        %s' % str(self.anchor_offset))
    if self.anchor_max_wakeup:
      print('Anchor max wakeup:    %s' % str(self.anchor_max_wakeup))
    if self.sunrise_adjusted:
      print('Sunrise with Offset:  %s' % str(self.sunrise_adjusted))
    print('Max wakeup:           %s' % str(self.max_wakeup))
    print('Wakeup time:          %s' % str(self.wakeup_time))
    print('delay:                %s' % str(self.delay))
    print('script:               "%s"' % str(self.script))

  def Message(self):
    if self.delay and self.delay > 0:
      wakeup_time = self.wakeup_time + datetime.timedelta(minutes=self.delay)
      delay_hours = self.delay / 60
      delay_minutes = self.delay % 60
      if delay_hours > 0:
        hour_plural = ''
        if delay_hours > 1:
          hour_plural = 's'
        delay_string = '.  Delayed by {} hour{} and {} minutes.'.format(
            delay_hours, hour_plural, delay_minutes)
      else:
        delay_string = '.  Delayed by {} minutes.'.format(
            delay_minutes)
    else:
      wakeup_time = self.wakeup_time
      delay_string = ''

    current_time = datetime.datetime.now()
    wakeup_midnight = wakeup_time.replace(
        hour=0, minute=0, second=0, microsecond=0)
    days = (wakeup_midnight - current_time.replace(
        hour=0, minute=0, second=0, microsecond=0)).days
    if days == 0:
      day_str = 'Today'
    elif days == 1:
      day_str = 'Tomorrow'
    else:
      day_str = 'In %d days' % days
    return '{day_string} at {hour}:{minute:02}{delay_string}'.format(
        day_string=day_str, hour=wakeup_time.hour,
        minute=wakeup_time.minute, delay_string=delay_string)

  def WaitUntilWakeup(self, max_delta=None):
    if self.delay and self.delay > 0:
      print('Delaying wakeup_time by {} minutes'.format(self.delay))
      wakeup_time = self.wakeup_time + datetime.timedelta(minutes=self.delay)
    else:
      wakeup_time = self.wakeup_time

    d = wakeup_time - datetime.datetime.now()
    if d.days < 0:
      raise ValueError('It is already after Wakeup time.')
    minutes, seconds = divmod(d.seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if max_delta and d >= max_delta:
      max_delta_minutes, max_delta_seconds = divmod(max_delta.seconds, 60)
      max_delta_hours, max_delta_minutes = divmod(max_delta_minutes, 60)
      days_string = ''
      if d.days == 1:
        days_string = '1 day and '
      elif d.days > 1:
        days_string = '%s days and ' % d.days
      print('Not sleeping, max_delta ' +
            '(%02d:%02d:%02d) is more than wait time (%s%02d:%02d:%02d)' % (
                max_delta_hours,max_delta_minutes,max_delta_seconds,
                days_string,
                hours,minutes,seconds))
      return False
    while d.days >= 0:
      minutes, seconds = divmod(d.seconds, 60)
      hours, minutes = divmod(minutes, 60)
      print('Sleep until wakeup time (waiting %02d:%02d:%02d)' % (
                hours,minutes,seconds))
      time.sleep(10)
      d = wakeup_time - datetime.datetime.now()
    return True


if __name__ == "__main__":
  sys.exit(1)

