from ConfigParser import ConfigParser
from time import sleep
import os, sys, signal, subprocess, shlex, getopt

def kill_firefox():
    for line in os.popen("ps xa"):
        fields = line.split()
        pid = fields[0]
        process = fields[4]
        if process.find("firefox") > 0:
            os.kill(int(pid), signal.SIGHUP)
            break

def ping_firefox():
    for line in os.popen("ps xa"):
        fields = line.split()
        process = fields[4]
        if process.find("firefox") > 0:
            return 1
    return 0    

# Initialization
config = ConfigParser()
config.read(os.getcwd() + "/fbtest.conf")

try:
    opts, args = getopt.getopt(sys.argv[1:], "s:v:p:")
except getopt.GetoptError, err:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)
# Retrieve variables from command line or config file
serverpath = config.get("run", "serverpath")
profile = config.get("run", "profile")
firebug_version = config.get("run", "firebug_version")
fbtest_version = config.get("run", "fbtest_version")
for o, a in opts:
    if o == "-s":
        serverpath = a
    elif o == "-v":
        firebug_version = a
        fbtest_version = a
    elif 0 == "-p":
        profile = a 
    else:
        assert False, "unhandled option"

# Find appropriate .xpi files based on the version, if they exist
firebug, fbtest = "", ""
for file in os.listdir(os.getcwd()):
    if file[:9 + len(firebug_version)] == "firebug-" + firebug_version + "X":
        firebug = file
    elif file[:8 + len(firebug_version)] == "firebug-" + firebug_version and firebug == "" :
        firebug = file
    elif file[:6 + len(fbtest_version)] == "fbtest" + fbtest_version and fbtest == "":
        fbtest = file
# Make sure version actually exists
if firebug == "":
    print "Couldn't find Firebug extension with version: " + firebug_version
    sys.exit(2)
elif fbtest == "":
    print "Couldn't find FBTest extension with version: " + fbtest_version
    sys.exit(2)
    
# If firefox is running, kill it (needed for mozrunner)
kill_firefox()

sleep(5)

print profile
p = subprocess.Popen(shlex.split("mozrunner -n -p " + profile + " --addons=\"" + os.getcwd() + "/" + firebug + "\",\"" + os.getcwd() + "/" + fbtest + "\""))
p = subprocess.Popen(shlex.split("firefox -runFBTests " + serverpath + "tests/content/testlists/firebug" + fbtest_version + ".html"))
    