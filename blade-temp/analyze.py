#!/usr/bin/env python

import sys
import re

warning = {
        'Enclosure': 22,
        'Onboard Administrator': 40,
        'Blade Bay': 24
        }

critical = {
        'Enclosure': 25,
        'Onboard Administrator': 45,
        'Blade Bay': 25
        }

global_state = 0

def print_current(data):
    print 'Sensor - Number - State - Current - Warning - Critical'
    for info in data:
        print '{0} - {1} - {2} - {3} - {4} - {5}'.format(info[0], info[1], info[2], info[3], warning[info[0]], critical[info[0]])

def decide(sensor, val):
    global global_state
    if int(val) > critical[sensor]:
        global_state = 2
        return 'CRITICAL'
    if int(val) > warning[sensor]:
        if global_state < 1:
            global_state = 1
        return 'WARNING'
    return 'OK'

def main():
    info = []
    for line in sys.stdin.readlines():
        tokens = re.split('\s{2,}', line)
        if re.match('Enclosure', tokens[0]):
            val = re.sub('C/.*', '', tokens[2])
            info.append(['Enclosure', 1, decide('Enclosure', val), val])
        if re.match('^Onboard', tokens[0]):
            val = re.sub('C/.*', '', tokens[3])
            info.append(['Onboard Administrator', tokens[1], decide('Onboard Administrator', val), val])
        if re.match('^Blade', tokens[0]):
            val = re.sub('C/.*', '', tokens[3])
            info.append(['Blade Bay', tokens[1], decide('Blade Bay', val), val])
    state = 'OK'
    if global_state == 1:
        state = 'WARNING'
    if global_state == 2:
        state = 'CRITICAL'
    print "Overall state is {0} . Enclosure temp is {1} (W/C {2}/{3})|".format(state, info[0][3], warning['Enclosure'], critical['Enclosure'])
    print_current(info)
    exit(global_state)

if __name__ == "__main__":
    main()
