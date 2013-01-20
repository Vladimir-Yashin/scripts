#!/bin/sh

[ $PAM_USER = "root" ] && exit 0;

/usr/sbin/setquota $PAM_USER $1 $2 0 0 -a
exit 0
