import sys

def main():
    for i in xrange(1000):
        print 'start %d' % i
    print 'woo'
    while True:
        line = sys.stdin.readline()
        print '> %s' % line
        if line == 'stop\n':
            return

main()
