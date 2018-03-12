#!/usr/bin/python

import os
import re
import sys
import threading
import time

def MyPrint(data):
  print('"' + data + '"')

def ControlLoop():
  fifo_path = '/tmp/switch_command.fifo'
  if os.path.exists(fifo_path):
    os.unlink(fifo_path)
  os.mkfifo(fifo_path)
  print('Created fifo: ' + fifo_path)
  quit = False
  while not quit:
    with open(fifo_path, 'r') as f:
      data = f.read().strip()
      print(data)
      m = re.match(r'print (\S+.*?)\s*$', data)
      if m:
        MyPrint(m.group(1))
      m = re.match(r'quit(?:\s.*)?$', data)
      if m:
        quit = True

control_loop_thread = threading.Thread(target=ControlLoop)
control_loop_thread.daemon = True
control_loop_thread.start()


control_loop_thread.join()
