#!/bin/sh

connected() {
    xrandr --fb 1920x1080 --output LVDS1 --auto --scale 1.405x1.406 --output HDMI1 --auto --primary
}

disconnected() {
    xrandr --fb 1366x768 --output LVDS1 --auto --scale 1x1 --primary --output HDMI1 --off
}

status=""
[ -f /sys/class/drm/card0-HDMI-A-1/status ] && status=$(cat /sys/class/drm/card0-HDMI-A-1/status)
[ -f /sys/class/drm/card1-HDMI-A-1/status ] && status=$(cat /sys/class/drm/card1-HDMI-A-1/status)

export XAUTHORITY=/home/booble/.Xauthority
export DISPLAY=:0.0

if [ "${status}" = disconnected ]; then
    eval disconnected
elif [ "${status}" = connected ]; then
    eval connected
fi
