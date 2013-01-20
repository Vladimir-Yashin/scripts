#!/bin/bash

SIGNAL_FILE="/tmp/video-helper-changed"

if [ ! -e $SIGNAL_FILE ]; then
    touch $SIGNAL_FILE
    chmod 666 $SIGNAL_FILE
fi

echo $HOME/.Xauthority > $SIGNAL_FILE
echo $DISPLAY >> $SIGNAL_FILE

# Force resolution fix at logon
/usr/local/bin/video-helper.sh
