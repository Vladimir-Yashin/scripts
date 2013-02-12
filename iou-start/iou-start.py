#!/usr/bin/env python

import sys
import os
import getopt
import ConfigParser
import re
import socket
import subprocess
import time
import signal

app_name = "iou-start"
app_version = "0.2"

class __GlobalData(object):
    base_id   = 100
    hostname  = socket.gethostname()
    iou_store = None
    workdir   = None
    respawn   = False
    debug     = False

    def get_id(self):
        self.base_id += 1
        return self.base_id - 1

    def __getitem__(self, item):
        return self.__getattr__(item)

    def __setitem__(self, item, val):
        return self.__setattr__(item, val)

    def __str__(self):
        return str(self.__dict__)

#FIXME: make GlobalData true static class
GlobalData = __GlobalData()
#class Routers(list):
#    pass
Routers = []
#FIXME: make Routers a class inheriting from list and add some useful methods to it

class Tun:
    _id       = None
    _log_file = None
    name      = None
    pid       = None
    br_name   = None

    def __init__(self, name):
        self._id = GlobalData.get_id()
        self.name = name

    def __str__(self):
        return "[%d] %s" % (self._id, self.name)

    def get_cmdline(self):
        return "%s/%s -t %s -p %s" % (GlobalData.iou_store, GlobalData.iou2net, self.name, self._id)

    def is_alive(self):
        # First check if process with self.PID is running
        check_pid = False
        if self.pid is not None:
            try:
                os.kill(self.pid, 0)
            except OSError:
                check_pid = False
            else:
                check_pid = True
        # Then check if interface with self.name exists
        check_name = check_if_iface_exists(self.name)

        #FIXME: something is wrong with check
        check_pid = check_name
        #FIXME: xwrapper is always spawning subprocess, so we can't rely on PID

        # Summing up
        if check_name == True and check_pid == True:
            return True
        elif check_name == False and check_pid == False:
            return False
        else:
            raise Exception("TUN alive check failed, PID check (%s) and ifname check (%s) gave different results" % (check_pid, check_name))

    """
    Run iou2net and add TUN to bridge if needed
    Takes: None
    Returns: Integer
    """
    def run(self):
        # Logging
        self._log_file = open("%s/%s.log" % (GlobalData.workdir, self.name), "w")
        # Running iou2net
        self.pid = sh(self.get_cmdline(), out=self._log_file)
        # Check if need to put this TUN into bridge
        if self.br_name is not None:
            # Wait until iou2net is fully started
            time.sleep(0.2)
            # Check if bridge exists
            if not check_if_iface_exists(self.br_name):
                sh("brctl addbr %s" % self.br_name, out=self._log_file)
            # Add interface to bridge (with all links down, just in case)
            sh("ip link set %s down" % self.name,    out=self._log_file)
            sh("ip link set %s down" % self.br_name, out=self._log_file)

            sh("brctl addif %s %s" % (self.br_name, self.name), out=self._log_file)

            sh("ip link set %s up" % self.name,    out=self._log_file)
            sh("ip link set %s up" % self.br_name, out=self._log_file)


        return self.pid

    """
    Stop iou2net instance
    Takes: None
    Returns: None
    """
    def kill(self):
        if self.is_alive():
            try:
                os.kill(self.pid, 2) #SIGINT
            except OSError:
                pass
        if not self._log_file is None:
            self._log_file.close()


class Connection:
    to_router   = None
    from_port   = None
    to_port     = None
    to_tun      = None

    def __str__(self):
        if self.to_tun is None:
            return "%s %s = %s %s\n" % (
                self.from_port,
                self.to_router,
                self.to_port
                )
        else:
            return "%s %s = TUN %s" % (
                    self.from_port,
                    self.to_tun
                    )

    def is_tun(self):
        return self.to_tun is not None

    def get_cmdline(self):
        if self.is_tun():
            return self.to_tun.get_cmdline()
        else:
            raise Exception("Asked cmdline for non TUN connection")


"""
IOU router entity, constructed for each router
section in config (template and real routers)
"""
class IouRouter(object):
    _id          = None
    _parent      = None
    _log_file    = None
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
                res.append("%s:%s@%s %s:0/0@%s\n" % (self._id, conn.from_port, GlobalData.hostname, conn.to_tun._id, GlobalData.hostname))
            else:
                res.append("%s:%s %s:%s\n" % (self._id, conn.from_port, conn.to_router._id, conn.to_port))
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
    Run router instance
    Takes: None
    Returns: Integer
    """
    def run(self):
        if not self.is_template() and not self.is_alive():
            # Use persistent NVRAM file tied to router name rather then ID
            real_file = GlobalData.workdir + "/nvram_" + self.name
            link_file = GlobalData.workdir + "/nvram_" + "{0:05d}".format(self._id)
            if not os.path.isfile(real_file):
                with open(real_file, "w") as f:
                    f.write("")
            if os.path.exists(link_file):
                os.remove(link_file)
            os.symlink(real_file, link_file)
            # Specifying log file for router instance
            self._log_file = open("%s/%s.log" % (GlobalData.workdir, self.name), "w")
            # Running
            self.pid = sh(self.get_cmdline(), out=self._log_file)
        return self.pid

    """
    Stop router
    Takes: None
    Returns: None
    """
    def kill(self):
        if self.is_alive():
            try:
                os.kill(self.pid, 2) #SIGINT
            except OSError:
                pass
            map(lambda conn: conn.is_tun() and conn.to_tun.kill(), self.conns)
        if not self._log_file is None:
            self._log_file.close()



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
                conn.from_port   = item
                val = val.split()
                if len(val) > 2:
                    raise Exception("Too many arguments to connection: [%s] %s" % (r.name, val))
                if val[0] == "tun":
                    conn.to_tun = Tun("tun_%s_%s" % (r.name, re.sub("\/", "_", conn.from_port)))
                    if len(val) == 2:
                        conn.to_tun.br_name = val[1]
                else:
                    conn.to_router = val[0]
                    conn.to_port   = val[1]
                r.conns.append(conn)
            else:
                # Just plain item=val
                setattr(r, item, val)
        Routers.append(r)

    # Postprocess, update references
    for r in Routers:
        # Update references for _parent and replace None values from it
        if hasattr(r, "parent"):
            r._parent = filter((lambda rtr: rtr.name == r.parent), Routers)[0]
            r.copy_from_parent()
        # Update conn.to_router with reference to router object
        for c in r.conns:
            if not c.is_tun():
                c.to_router = filter((lambda rtr: rtr.name == c.to_router), Routers)[0]

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
Run 'cmd' in Linux shell redirecting output to STDOUT or to supplied file descriptor,
returns PID
Takes: String, TextStream
Returns: Integer
"""
def sh(cmd, out = sys.stdout):
    if is_debugging():
        out.write("DEBUG: sh: %s\n" % cmd)
    return subprocess.Popen(cmd, shell=True, cwd=GlobalData.workdir, stdout=out, stderr=subprocess.STDOUT).pid

"""
Callback for SIGINT signal
Used for graceful shutdown upon receiving Ctrl+C in terminal
Takes: None
Returns: None
"""
def ctrlc_handler(signum, name):
    print("SIGINT catched, terminating...")
    map(lambda r: r.kill(), Routers)
    # Let them shutdown
    time.sleep(2)
    print_status()
    sys.exit(0)

"""
Try to run again each router if it crashed
Takes: None
Returns: None
"""
#FIXME: not respawning routers, because when router dies it's parent sh process is stuck in <defunct> state and is
# still considered to be alive
def respawn():
    map(lambda r: r.run(), Routers)

"""
Print table with TUN and routers status
Takes: None
Returns: None
"""
def print_status():
    # Check if all TUN-s are running
    print("TUN\tPID\tALIVE")
    for r in Routers:
        for conn in r.conns:
            if conn.is_tun():
                if conn.to_tun.is_alive():
                    print("%s\t\t%s\tYES" % (conn.to_tun.name, conn.to_tun.pid))
                else:
                    print("%s\t\t%s\tNO" % (conn.to_tun.name,conn.to_tun.pid))
    print("")

    # Showing router table
    print("CONSOLE\tROUTER\tRAM\tPID\tALIVE")
    for r in Routers:
        if not r.is_template():
            if r.is_alive():
                check = "YES"
            else:
                check = "NO"
            print("%s\t%s\t%s\t%s\t%s" % (r.console, r.name, r.ram, r.pid, check))
    print("")

"""
Check if interface with 'ifname' exists in OS
Takes: String
Returns: Boolean
"""
def check_if_iface_exists(ifname):
    # Quick and dirty hack, works only on Linux
    check = False
    with open("/proc/net/dev", "r") as f:
        for line in f:
            if re.match(ifname, line):
                check = True
                break
    return check

"""
Returns True if debug was enabled in config file
You can use this function to print conditional output
Takes: None
Returns: Boolean
"""
def is_debugging():
    return GlobalData.debug.lower() in ["true", "yes", "1", "y", "t"]

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
    read_config(config_path)

    # Debug print
    #print(GlobalData)
    #for r in Routers:
    #    print(r)

    # Writing NETMAP and IOURC files
    with open(GlobalData.workdir + "/NETMAP", "w") as f:
        for r in Routers:
            for line in r.get_netmap():
                f.write(line)
    with open(GlobalData.workdir + "/iourc", "w") as f:
        f.write("[license]\n%s = %s;\n" % (GlobalData.hostname, GlobalData.license) )

    # Running commands
    print("Starting routers...")
    respawn()
    # Waiting for all routers to start
    time.sleep(10)
    # Running iou2net instances
    print("Starting iou2net instances...")
    for r in Routers:
        for conn in r.conns:
            if conn.is_tun():
                conn.to_tun.run()


    # Setting Ctrl+C handler for graceful shutdown
    signal.signal(signal.SIGINT, ctrlc_handler)

    # Entering main loop
    while True:
        if GlobalData.respawn.lower() in ["true", "yes", "1", "y", "t"]:
            respawn()
        print_status()
        raw_input("Press ENTER to refresh or Ctrl+C to exit and kill all IOU instances...\n")


if __name__ == "__main__":
    main()


