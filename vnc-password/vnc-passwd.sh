#!/bin/bash

read user
read pass

\su $user -c "echo '${pass}' | sudo -S true"

