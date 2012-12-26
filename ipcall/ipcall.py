#!/usr/bin/env python

import keyring
import subprocess
import getpass
import curl
import getopt
import sys
import re
import pycurl
import urllib
from vsgui.api import *

pwstorage = "ipCall"
phone_ip = "10.48.10.32"

def reset_password(username):
    keyring.set_password(pwstorage, username, "")

def get_password(username, storage):
    password = keyring.get_password(storage, username)
    if password == None or password == "":
        print("Password not found in keyring, trying to request...")
        password = ask_passwd("Please enter your password:")
        keyring.set_password(storage, username, password)
    return password

def usage():
    print("Usage: ipcall.py [-p IPPHONE_IP] <number to call>")

def call(username, password, number):
    print("Got number %s" % number)
    number = re.sub("^\+", "000", number)
    number = re.sub("[^0-9]", "", number)
    print("Calling %s" % number)
    c = pycurl.Curl()
    c.setopt(pycurl.POST, 1)
    #fout = StringIO.StringIO()
    #c.setopt(pycurl.WRITEFUNCTION, fout.write)
    userpwd = "%s:%s" % (username, password)
    c.setopt(pycurl.USERPWD, userpwd.encode("ascii"))
    c.setopt(pycurl.URL, "http://%s/CGI/Execute" % phone_ip)
    c.setopt(pycurl.POSTFIELDS, urllib.urlencode({
    "XML": """
    <CiscoIPPhoneExecute>
        <ExecuteItem URL='Dial:%s' />
    </CiscoIPPhoneExecute>
    """ % number,
    "B1": "Submit"
    }) )
    c.perform()
    result = c.getinfo(pycurl.RESPONSE_CODE)
    print("Result code: %s" % result)
    if result != 201:
        error("Error %s, look at console output for details" % result)

def main():
    opts, args = getopt.getopt(sys.argv[1:], "dp:u:")
    if len(args) < 1:
        usage()
        sys.exit(1)

    username = getpass.getuser()
    for o, v in opts:
        if o == "-u":
            print("Using alternative username %s" % v)
            username = v
        if o == "-d":
            print("Removing saved password from keyring")
            reset_password(username)
        if o == "-p":
            print("Using supplied phone IP %s" % v)
            phone_ip = v
    password = get_password(username, pwstorage)
    print("Got password for %s" % username)
    call(username, password, "".join(args))

if __name__ == "__main__":
    main()

