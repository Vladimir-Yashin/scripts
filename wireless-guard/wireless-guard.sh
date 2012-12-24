#!/bin/sh

while true; do
    #gw=`ip ro show 0.0.0.0/0 | grep wlan0 | awk '{print $3}'`
    #if [ $gw != "" ]; then
        #echo "Pinging $gw..."
    #fi
    gw="8.8.8.8"
    ping -c 5 $gw > /dev/null 2>&1
    res=$?
    if ! [ $res -eq 0 ]; then
        date
        rmmod rtl8192ce
        modprobe rtl8192ce
        echo "Module reloaded"
    fi
    sleep 20
done

