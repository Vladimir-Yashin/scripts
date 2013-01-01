#!/bin/bash

# This script reacts to changes on VGA connector and sends signal to user-level script via file creation
# When script is run by root it means it was called from udev, so it creates special file
# When script is run by user it checks if signal file exists and changes monitor configuration

SIGNAL_FILE="/tmp/video-helper-changed"

if [ ! -e $SIGNAL_FILE ]; then
    touch $SIGNAL_FILE
    chmod 666 $SIGNAL_FILE
fi

export XAUTHORITY=`cat $SIGNAL_FILE | head -1`
export DISPLAY=`cat $SIGNAL_FILE | head -2 | tail -1`

#Adapt below values to suite your monitors
LVDS_W=1024
LVDS_H=600
VGA_W=1280
VGA_H=1024
SCALE_W=`echo "scale=6; ${VGA_W}/${LVDS_W}" | bc`
SCALE_H=`echo "scale=6; ${VGA_H}/${LVDS_H}" | bc`

connected() {
    xrandr --fb ${VGA_W}x${VGA_H} --output LVDS1 --auto --scale ${SCALE_W}x${SCALE_H} --output VGA1 --auto --primary
}

disconnected() {
    xrandr --fb ${LVDS_W}x${LVDS_H} --output LVDS1 --auto --scale 1x1 --primary --output VGA1 --off
}

status=""
[ -f /sys/class/drm/card0-VGA-1/status ] && status=$(cat /sys/class/drm/card0-VGA-1/status)
[ -f /sys/class/drm/card1-VGA-1/status ] && status=$(cat /sys/class/drm/card1-VGA-1/status)

if [ "${status}" = disconnected ]; then
    eval disconnected
elif [ "${status}" = connected ]; then
    eval connected
fi
