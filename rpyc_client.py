#!/usr/bin/python
import rpyc
import time

def notify():
  print('button pressed')

print ('before connection')
service_connection = rpyc.connect("localhost", 18861)
print ('before rpc')
# value = service_connection.root.wait_for_button(notify)
# print ('rpc returned {}'.format(value))
# while True:
#   time.sleep(1)
value = service_connection.root.wait_for_button()
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button()
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button()
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button()
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button()
print ('rpc returned {}'.format(value))
