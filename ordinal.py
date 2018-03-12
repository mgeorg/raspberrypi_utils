#!/usr/bin/python

import sys

num_str = sys.argv[1].strip().lstrip('0')
if not num_str:
  num_str = '0'
num = int(num_str)

ordinal = [
  'zeroth',
  'first',
  'second',
  'third',
  'fourth',
  'fifth',
  'sixth',
  'seventh',
  'eighth',
  'ninth',
  'tenth',
  'eleventh',
  'twelfth',
  'thirteenth',
  'fourteenth',
  'fifteenth',
  'sixteenth',
  'seventeenth',
  'eighteenth',
  'nineteenth',
  'twentieth',
  'twenty-first',
  'twenty-second',
  'twenty-third',
  'twenty-fourth',
  'twenty-fifth',
  'twenty-sixth',
  'twenty-seventh',
  'twenty-eighth',
  'twenty-ninth',
  'thirtieth',
  'thirty-first',
  'thirty-second',
  'thirty-third',
  'thirty-fourth',
  'thirty-fifth',
  'thirty-sixth',
  'thirty-seventh',
  'thirty-eighth',
  'thirty-ninth',
  'fortieth',
  'forty-first',
  'forty-second',
  'forty-third',
  'forty-fourth',
  'forty-fifth',
  'forty-sixth',
  'forty-seventh',
  'forty-eighth',
  'forty-ninth',
]

print(ordinal[num])

