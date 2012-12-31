#!/usr/bin/env python

import sys
import os
import copy
import getopt
import ConfigParser
import re

app_name = "iou-start"
app_version = "0.1"

def print_version():
    print("%s version %s" % (app_name, app_version) )

def print_usage():
    print("""
    Python script that starts multiple IOU instances in separate screen/tmux session
    Usage: %s [-v | --version] [-u | --usage] [-h | --help] -c <config_file>
    """ % (app_name) )

def main():
    #Parsing cmdline options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vuhc:", ["version", "usage", "help", "config"])
    except getopt.GetoptError as err:
        print str(err) # will print something like "option -a not recognized"
        print_usage()
        sys.exit(2)

    config_path = False
    for o, v in opts:
        if o in ("-v", "--version"):
            print_version()
            sys.exit(0)
        if o in ("-u", "--usage", "-h", "--help"):
            print_usage()
            sys.exit(0)
        if o in ("-c", "--config"):
            config_path = v
    if not config_path:
        print("Required option -c missing")
        print_usage()
        sys.exit(3)

    # Reading configuration file
    try:
        global_data, routers = load_config(config_path)
    except Exception as err:
        print("Error reading config file: %s" % err)
        sys.exit(4)

    print("GLOBAL = %s" % global_data)
    print("ROUTERS = %s" % routers)

    # Generating NETMAP file
    # TODO

def load_config(path):
    # Data format definition
    global_data = {
        "base_id": 100,
        "workdir": False,
        "iou"    : False,
        "wrapper": False,
        "iou2net": False,
            }
    router_template = {
            "name"     : "router",
            "id"       : 0,
            "console"  : 0,
            "iou"      : False,
            "mem"      : 256,
            "nvram"    : 32,
            "ethernets": 1,
            "serials"  : 1,
            }

    config = ConfigParser.ConfigParser()
    config.read(path)

    print("Reading config file %s" % path)

    if not config.has_section("global"):
        raise Exception("[global] section missing")

    print("Found [global] section")
    if config.has_option("global", "base_id"):
        global_data["base_id"] = config.get("global", "base_id")
    global_data["workdir"] = config.get("global", "workdir")
    global_data["iou"]     = config.get("global", "iou")
    global_data["wrapper"] = config.get("global", "wrapper")
    global_data["iou2net"] = config.get("global", "iou2net")
    for item, val in config.items("global"):
        if not item in global_data:
            print("Unused variable %s" % item)

    routers = []
    for sec in config.sections():
        if sec == "global":
            continue
        print("Found router section [%s]" % sec)
        r = {}
        r["name"] = sec
        r["id"] = global_data["base_id"]
        global_data["base_id"] += 1
        r["console"] = config.get(sec, "console")
        if config.has_option(sec, "iou"):
            r["iou"] = config.get(sec, "iou")
        else:
            r["iou"] = global_data["iou"]
        if config.has_option(sec, "mem"):
            r["mem"] = config.get(sec, "mem")
        else:
            r["mem"] = router_template["mem"]
        if config.has_option(sec, "nvram"):
            r["nvram"] = config.get(sec, "nvram")
        else:
            r["nvram"] = router_template["nvram"]
        if config.has_option(sec, "ethernets"):
            r["ethernets"] = config.get(sec, "ethernets")
        else:
            r["ethernets"] = router_template["ethernets"]
        if config.has_option(sec, "serials"):
            r["serials"] = config.get(sec, "serials")
        else:
            r["serials"] = router_template["serials"]
        r["conns"] = []
        for item, val in config.items(sec):
            if re.match("^[0-9]/[0-9]+", item):
                r["conns"] += (item, val)
        routers.append(r)

    return (global_data, routers)

if __name__ == "__main__":
    main()

