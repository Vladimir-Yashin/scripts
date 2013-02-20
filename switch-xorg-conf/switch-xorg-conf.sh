#!/bin/bash

dockstation_config="xorg.conf.dockstation"
standalone_config="xorg.conf.standalone"
dm="lightdm"

dock() {
    echo "Current config is 'dock', replacing xorg.conf..."
    rm xorg.conf
    ln -s $standalone_config xorg.conf
    echo "Stopping X..."
    stop $dm
    echo "Turning NVIDIA off..."
    rmmod nvidia
    echo OFF > /proc/acpi/bbswitch
    echo "State of bbswitch is `cat /proc/acpi/bbswitch`"
    echo "Starting X..."
    start $dm
}

standalone() {
    echo "Current config is 'standalone', replacing xorg.conf..."
    rm xorg.conf
    ln -s $dockstation_config xorg.conf
    echo "Stopping X..."
    stop $dm
    echo "Turning NVIDIA on..."
    echo ON > /proc/acpi/bbswitch
    echo "State of bbswitch is `cat /proc/acpi/bbswitch`"
    modprobe nvidia_current
    echo "Starting X..."
    start $dm
}

cd /etc/X11
if [[ `ls -la xorg.conf` =~ "xorg.conf -> $dockstation_config" ]]; then
    eval dock
elif [[ `ls -la xorg.conf` =~ "xorg.conf -> $standalone_config" ]]; then
    eval standalone
else
    echo "Uknown configuration detected, check /etc/X11/xorg.conf"
fi
