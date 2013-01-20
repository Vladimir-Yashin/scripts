#!/usr/bin/env python

import sys
import os
import getpass
import getopt
import subprocess
import keyring
import pexpect

rdp_server="term01"
key_name="xfreerdp"
passwd_retries=3

""" Returns password for current user even if it is not present in keyring """
def getset_password(username):
    passwd = keyring.get_password(key_name, username)
    if passwd == None or passwd == "":
        p = subprocess.Popen(
                ["zenity", "--title='Password'", "--text=Please enter your password\nUsername: "+username, "--entry", "--hide-text"],
                stdout=subprocess.PIPE
                )
        out, err = p.communicate()
        if p.returncode != 0:
            raise Exception("Password prompt program terminated unexpectedly")
        passwd = out
        # add received password to keyring
        keyring.set_password(key_name, username, passwd)
    return passwd

def del_password(username):
    keyring.set_password(key_name, username, "")

def show_error_box(text):
    subprocess.call(["zenity", "--text="+text, "--error"])

def spawn_xfreerdp(username, passwd, cmd):
    cmdline = "xfreerdp -u %s --ignore-certificate -x m -z" % (username)
    if cmd != "":
        cmd = cmd.replace("$USERNAME$", username, 1)
        cmdline += " --app --plugin /usr/local/lib/freerdp/rail.so --data '||%s' -- " % (cmd)
    homedir = os.getenv("HOME") + "/Documents"
    cmdline += " --plugin cliprdr --plugin rdpdr --data printer disk:disk:/media/disk disk:home:%s -- %s" % (homedir, rdp_server)
    print cmdline
    p = pexpect.spawn(cmdline)
    p.expect("Password:")
    p.sendline(passwd)
    if p.isalive():
        p.wait()
    return p.exitstatus

def main():
    username = getpass.getuser()
    cmd = ""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "u:c:")
        for o, a in opts:
            if o == "-u":
                username = a
            if o == "-c":
                cmd = a
    except getopt.GetoptError, err:
        username = username

    retries = 0
    while retries < passwd_retries:
        passwd = getset_password(username)
        retval = spawn_xfreerdp(username, passwd, cmd)
        if retval == 131:
            retries += 1
            del_password(username)
            show_error_box("Wrong password. Please, try again")
        else:
            break
    if retries >= passwd_retries:
        del_password(username)
        show_error_box("Maximum retries number reached")
    elif retval in (5, 11): #actually not an error
        pass
    elif retval != 0:
        del_password(username)
        show_error_box("Error number %i occured" % retval)

if __name__ == '__main__':
    main()
