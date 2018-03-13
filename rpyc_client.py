#!/usr/bin/python
import rpyc

print ('before connection')
service_connection = rpyc.connect("localhost", 18861)
print ('before rpc')
value = service_connection.root.wait_for_button(1)
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button(2)
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button(3)
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button(4)
print ('rpc returned {}'.format(value))
value = service_connection.root.wait_for_button(5)
print ('rpc returned {}'.format(value))
