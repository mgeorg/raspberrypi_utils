
import os
import sys
import datetime
import json

class PubSubError(Exception):
  pass

_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

class SimplePubSub:

  def __init__(self, location):
    self.location = location
    self.last_timestamp = datetime.datetime.now()
    if not os.path.isfile(self.location):
      return
    with open(self.location, 'r') as f:
      for line in f:
        try:
          data = json.loads(line)
          if isinstance(data, list) and len(data) == 3:
            t = datetime.datetime.strptime(data[0], _DATE_FORMAT)
            if t > self.last_timestamp:
              # This shouldn't happen.
              self.last_timestamp = t
        except ValueError:
          continue

  def Publish(self, origin, message):
    with open(self.location, 'a') as f:
      time_str = datetime.datetime.now().strftime(_DATE_FORMAT)
      if not isinstance(origin, str):
        raise PubSubError('origin must be a string')
      if not isinstance(message, str):
        raise PubSubError('message must be a string')
      f.write(json.dumps((time_str, origin, message)) + '\n')

  def Poll(self):
    with open(self.location, 'r') as f:
      current_count = 0
      for line in f:
        try:
          data = json.loads(line)
          if isinstance(data, list) and len(data) == 3:
            t = datetime.datetime.strptime(data[0], _DATE_FORMAT)
        except ValueError:
          continue
        # Found something we haven't seen yet.
        if t > self.last_timestamp:
          self.last_timestamp = t
          return (t, data[1], data[2])
    return None

