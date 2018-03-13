#!/usr/bin/python
import rpyc
import rpyc.utils.server
import time

global global_count
global_count = 0

class WaitForButtonService(rpyc.Service):
  def on_connect(self, unused_conn=None):
    self.sleep_count = 0
  def exposed_wait_for_button(self, sleep_time):
    global global_count
    time.sleep(sleep_time)
    self.sleep_count += sleep_time
    global_count += sleep_time
    return (self.sleep_count, global_count)

server_thread = rpyc.utils.server.ThreadedServer(
  WaitForButtonService, port=18861)
server_thread.start()
