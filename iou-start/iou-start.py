#!/usr/bin/env python

import sys
import os
import copy
import getopt
import ConfigParser
import re
import socket
import subprocess
import time
import shlex

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

    try:
        tun_connections = write_netmap_file(global_data, routers)
    except Exception as err:
        print("Error writing NETMAP file: %s" % err)
        sys.exit(4)

    try:
        run_commands(global_data, routers, tun_connections)
    except Exception as err:
        print("Error executing commands: %s" % err)
        sys.exit(4)

    time.sleep(100000000)

def run_commands(global_data, routers, tun_connections):
    print("Starting routers...")
    for r in routers:
        cmd = "%s -m %s -p %s -- -e %s -s %s -m %s -n %s -q %s" % (
            global_data["wrapper"],
            r["iou"],
            r["console"],
            r["ethernets"],
            r["serials"],
            r["mem"],
            r["nvram"],
            r["id"])
        print(cmd)
        out_f = open("%s/%s.log" % (global_data["workdir"], r["name"]), "w")
        subprocess.Popen(cmd, shell=True, cwd=global_data["workdir"], stdout=out_f, stderr=subprocess.STDOUT)

    time.sleep(5)
    print("Starting TAPs...")
    for t in tun_connections:
        cmd = "%s -t %s -p %s" % (global_data["iou2net"], t["name"], t["id"])
        print(cmd)
        subprocess.Popen(cmd, shell=True, cwd=global_data["workdir"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        time.sleep(2)
        cmd = "ip link set %s up" % t["name"]
        print(cmd)
        subprocess.Popen(cmd, shell=True)

def write_netmap_file(global_data, routers):
    tun_connections = []
    # Generating NETMAP file
    with open(global_data["workdir"] + "/NETMAP", "w") as f:
        for r in routers:
            for conn_from_port, conn_to_combined in r["conns"]:
                if conn_to_combined == "tun":
                    tun = {
                            "id": global_data["base_id"],
                            "name": "tun_" + r["name"] + "_" + re.sub("\/", "_", conn_from_port)
                            }
                    global_data["base_id"] += 1
                    tun_connections.append(tun)
                    hostname = socket.gethostname()
                    f.write("%s:%s@%s %s:0/0@%s\n" % (r["id"], conn_from_port, hostname, tun["id"], hostname) )
                else:
                    m = re.search("([a-zA-Z0-9]+)\s([0-9]/[0-9]+)", conn_to_combined)
                    conn_to_router_name = m.group(1)
                    conn_to_port = m.group(2)
                    conn_to_router = filter(lambda r: r["name"] == conn_to_router_name, routers)[0]
                    f.write("%s:%s %s:%s\n" % (r["id"], conn_from_port, conn_to_router["id"], conn_to_port) )

    # License file
    with open(global_data["workdir"] + "/iourc", "w") as f:
        f.write("[license]\n%s = %s;\n" % (socket.gethostname(), global_data["license"]) )

    return tun_connections

def load_config(path):
    # Data format definition
    global_data = {
        "base_id"     : 100,
        "workdir"     : False,
        "iou"         : False,
        "wrapper"     : False,
        "iou2net"     : False,
        "telnet"      : False,
        "tmux_session": "iou",
        "license"     : False,
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
            "conns"    : [],
            }

    config = ConfigParser.ConfigParser()
    config.read(path)

    print("Reading config file %s" % path)

    if not config.has_section("global"):
        raise Exception("[global] section missing")

    if config.has_option("global", "base_id"):
        global_data["base_id"] = int(config.get("global", "base_id"))
    global_data["workdir"] = os.path.expanduser(config.get("global", "workdir"))
    global_data["iou"]     = os.path.expanduser(config.get("global", "iou"))
    global_data["wrapper"] = os.path.expanduser(config.get("global", "wrapper"))
    global_data["iou2net"] = os.path.expanduser(config.get("global", "iou2net"))
    global_data["telnet"]  = os.path.expanduser(config.get("global", "telnet"))
    global_data["license"] = config.get("global", "license")
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
                r["conns"].append((item, val))
        routers.append(r)

    return (global_data, routers)

if __name__ == "__main__":
    main()


