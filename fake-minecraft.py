#!/usr/bin/python
import sys
from time import time

def main():
    start = time()

    for i in xrange(1000):
        print 'start %d' % i
    print 'woo'
    while True:
        line = sys.stdin.readline()
        print '> %s' % line.strip()
        if line == 'stop\n':
            return
        if line == 'list\n':
            if start + 30 < time():
                print 'There are 0/20 players online:'
            else:
                print 'There are 3/20 players online:'

main()
