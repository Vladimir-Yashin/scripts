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
app_version = "0.2"

class __GlobalData(object):
    base_id   = 100
    hostname  = socket.gethostname()
    iou_store = None
    workdir   = None

    def get_id(self):
        self.base_id += 1
        return self.base_id - 1

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __setitem__(self, item, val):
        return self.__setattr__(item, val)

    def __str__(self):
        return str(self.__dict__)

GlobalData = __GlobalData()
#class Routers(list):
#    pass
Routers = []

class Tun:
    _id = None
    name = None
    pid  = None

    def __init__(self, name):
        self._id = GlobalData.get_id()
        self.name = name

    def __str__(self):
        return "[%d] %s" % (self._id, self.name)

    def get_cmdline(self):
        return "%s/%s -t %s -p %s" % (GlobalData.iou_store, GlobalData.iou2net, self.name, self._id))

    def is_alive(self):
        # First check if process with self.PID is running
        check_pid = False
        if self.pid is None:
            check_pid = False
        else:
            try:
                os.kill(self.pid, 0)
            except OSError:
                check_pid = False
            else:
                check_pid = True
        # Then check if interface with self.name exists
        # Quick and dirty hack, works only on Linux
        check_name = False
        with open("/proc/net/dev", "r") as f:
            for line in f:
                if re.match(self.name, line):
                    check_name = True
                    break

        # Summing up
        if check_name == True and check_pid == True:
            return True
        elif check_name == False and check_pid == False:
            return False
        else:
            raise Exception("TUN alive check failed, PID check and ifname check gave different results")

class Connection:
    from_router = None
    to_router   = None
    from_port   = None
    to_port     = None
    to_tun      = None

    def __str__(self):
        if self.to_tun is None:
            return "%s %s = %s %s\n" % (
                self.from_router,
                self.from_port,
                self.to_router,
                self.to_port
                )
        else:
            return "%s %s = TUN %s" % (
                    self.from_router,
                    self.from_port,
                    self.to_tun
                    )

    def is_tun(self):
        return to_tun is not None

    def get_cmdline(self):
        if self.is_tun():
            return self.to_tun.get_cmdline()
        else:
            raise Exception("Asked cmdline for not TUN connection")


"""
IOU router entity, constructed for each router
section in config (template and real routers)
"""
class IouRouter(object):
    _id          = None
    _parent      = None
    name         = None
    image        = None
    console      = None
    ethernets    = None
    serials      = None
    ram          = None
    nvram        = None
    conns        = []
    pid          = None

    def __init__(self, name):
        self._id = GlobalData.get_id()
        self.name = name

    def __str__(self):
        res = "[%s]\n" % self.name
        for item in self.__dict__:
            if item == "_parent":
                res += "%s = %s\n" % (item, self.__dict__[item]._id)
            else:
                res += "%s = %s\n" % (item, self.__dict__[item])

        res += "cmdline = %s\n" % self.get_cmdline()

        for c in self.conns:
            res += "%s\n" % c

        return res

    """
    Check if this router was created from router template in config file
    Router is considered real if it has console port defined in config
    Takes: None
    Returns: Boolean
    """
    def is_template(self):
        return self.console is None

    """
    This function is called while reading config file
    It fills missing fields in router using parent template
    If parent is not available it does nothing and you should
    expect an error trying to read missing fields in future
    Takes: None
    Returns: None
    """
    def copy_from_parent(self):
        if self._parent is None:
            return
        else:
            self._parent.copy_from_parent() # for multitier inheritence (prone to loops!)
            for param in ["image", "ethernets", "serials", "ram", "nvram"]:
                if getattr(self, param) is None:
                    setattr(self, param, getattr(self._parent, param))

    """
    Return a cmdline for running this particular IOU router
    Takes: None
    Returns: None
    """
    def get_cmdline(self):
        if self.is_template():
            return ""
        else:
            return "%s/%s -m %s/%s -p %s -- -e %s -s %s -m %s -n %s -q %s" % (
                GlobalData.iou_store,
                GlobalData.wrapper,
                GlobalData.iou_store,
                self.image,
                self.console,
                self.ethernets,
                self.serials,
                self.ram,
                self.nvram,
                self._id
                )

    """
    Produce a list of NETMAP lines for connections from this router,
    both for local routers and TUNs
    Takes: None
    Returns: list[String]
    """
    def get_netmap(self):
        res = []
        for conn in self.conns:
            if conn.is_tun():
                res.append("%s:%s@%s %s:0/0@%s\n" % (conn.from_router, conn.from_port, GlobalData.hostname, conn.to_tun._id, GlobalData.hostname))
            else:
                res.append("%s:%s %s:%s\n" % (conn.from_router, conn.from_port, conn.to_router, conn.to_port))
        return res

    """
    Check if router is still running
    Takes: None
    Returns: Boolean
    """
    def is_alive(self):
        if self.pid is None:
            return False
        try:
            os.kill(self.pid, 0)
        except OSError:
            return False
        else:
            return True


"""
Read configuration file and create all router structures
Takes: String
Returns: None
"""
def read_config(path):
    print("Reading config file %s" % path)
    config = ConfigParser.ConfigParser()
    config.read(path)

    # Reading Global section
    for item, val in config.items("global"):
        GlobalData[item] = os.path.expanduser(val)

    # All other sections are considered to be Router sections
    for sec in config.sections():
        if sec == "global":
            continue
        r = IouRouter(sec)
        r.conns = []
        for item, val in config.items(sec):
            if re.match("^[0-9]/[0-9]+", item):
                # We found connection
                conn = Connection()
                conn.from_router = sec
                conn.from_port   = item
                if val == "tun":
                    conn.to_tun = Tun("tun_%s" % re.sub("\/", "_", conn.from_port))
                else:
                    m = re.search("([a-zA-Z0-9]+)\s([0-9]/[0-9]+)", val)
                    conn.to_router   = m.group(1)
                    conn.to_port     = m.group(2)
                r.conns.append(conn)
            else:
                # Just plain item=val
                setattr(r, item, val)
        Routers.append(r)

    # Update references for _parent and replace None values from it
    for r in Routers:
        if hasattr(r, "parent"):
            r._parent = filter((lambda rtr: rtr.name == r.parent), Routers)[0]
            r.copy_from_parent()

"""
Prints app version in terminal
Takes: None
Returns: None
"""
def print_version():
    print("%s version %s" % (app_name, app_version) )

"""
Prints usage
Takes: None
Returns: None
"""
def print_usage():
    print("""
    Python script that starts multiple IOU instances
    Usage: %s [-v | --version] [-u | --usage] [-h | --help] -c <config_file>
    """ % (app_name) )

"""
Callback for SIGINT signal
Used for graceful shutdown upon receiving Ctrl+C in terminal
Takes: None
Returns: None
"""
def ctrlc_handler():
    print("SIGINT catched, terminating...")
    for r in Routers:
        if r.is_alive():
            try:
                os.kill(r.pid, 2) #SIGINT
            except OSError:
                pass
            for conn in r.conns:
                if conn.is_tun() and conn.is_alive():
                    try:
                        os.kill(conn.to_tun.pid, 2) #SIGINT
                    except OSError:
                        pass
    # Let them shutdown
    time.sleep(2)
    print_status()
    sys.exit(0)


"""
Print table with TUN and routers status
Takes: None
Returns: None
"""
def print_status():
    # Check if all TUN-s are running
    print("TUN\tALIVE")
    for r in Routers:
        for conn in r.conns:
            if conn.is_tun():
                if conn.to_tun.is_alive():
                    print("%s\tYES" % (conn.to_tun.name))
                else:
                    print("%s\tNO" % (conn.to_tun.name))
    print("")

    # Showing router table
    print("CONSOLE\tROUTER\tRAM\tPID\tALIVE")
    for r in Routers:
        if not r.is_template:
            if r.is_alive():
                check = "NO"
            else:
                check = "YES"
            print("%s\t%s\t%s\t%s\t%s" % (r.console, r.name, r.ram, r.pid, check))
    print("")

"""
MAIN
"""
def main():
    #Parsing cmdline options
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vuhc:", ["version", "usage", "help", "config"])
    except getopt.GetoptError as err:
        print str(err) # will print something like "option -a not recognized"
        print_usage()
        sys.exit(2)

    config_path = None
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
        read_config(config_path)
    except Exception as err:
        print("Error reading config file: %s" % err)
        sys.exit(4)

    # Debug print
    #print(GlobalData)
    #for r in Routers:
    #    print(r)

    # Writing NETMAP and IOURC files
    try:
        with open(GlobalData.workdir + "/NETMAP", "w") as f:
            for r in Routers:
                for line in r.get_netmap():
                    f.write(line)
        with open(GlobalData.workdir + "/iourc", "w") as f:
            f.write("[license]\n%s = %s;\n" % (GlobalData.hostname, GlobalData.license) )
    except Exception as err:
        print("Error writing NETMAP and IOURC files: %s" % err)
        sys.exit(4)

    # Running commands
    try:
        # Running just real routers
        for r in Routers:
            if not r.is_template():
                cmd = r.get_cmdline()
                # print(cmd)
                # Specifying log file for router instance
                out_f = open("%s/%s.log" % (GlobalData.workdir, r.name), "w")
                # Running
                r.pid = subprocess.Popen(cmd, shell=True, cwd=GlobalData.workdir, stdout=out_f, stderr=subprocess.STDOUT).pid
                # print(r.pid)
        # Running iou2net instances
        for r in Routers:
            for conn in r.conns:
                if conn.is_tun():
                    cmd = conn.get_cmdline()
                    print(cmd)
                    conn.to_tun.pid = subprocess.Popen(cmd, shell=True, cwd=GlobalData.workdir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except Exception as err:
        print("Error executing commands: %s" % err)
        sys.exit(4)

    # Waiting for all routers to start
    time.sleep(5)

    # Setting Ctrl+C handler for graceful shutdown
    signal.signal(signal.SIGINT, ctrlc_handler)

    # Entering main loop
    while True:
        print_status()
        raw_input("Press ENTER to refresh or Ctrl+C to exit and kill all IOU instances...")


if __name__ == "__main__":
    main()


