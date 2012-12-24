#!/bin/bash

## At first you have to ssh manually, for ssh not to ask about keys


cd /home/icinga/bin/blade_temp
./sshlogin.exp Administrator 'strong_password' 10.0.1.8 'show enclosure temp' 'exit' | ./analyze.py

