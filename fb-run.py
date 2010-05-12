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

# Initialization
config = ConfigParser()
config.read("./fb-test-runner.config")
# Retrieve variables from command line or config file
serverpath = config.get("run", "serverpath")
profile = config.get("run", "profile")
firebug_version = config.get("run", "firebug_version")
try:
    opts, args = getopt.getopt(sys.argv[1:], "s:v:p:")
except getopt.GetoptError, err:
    print str(err) 
    sys.exit(2)
for o, a in opts:
    if o == "-s":
        serverpath = a
    elif o == "-v":
        firebug_version = a
    elif 0 == "-p":
        profile = a 
    else:
        assert False, "unhandled option"



serverpath = serverpath + "firebug" + firebug_version

# Grab the extensions
os.system("wget " + serverpath + "/firebug.xpi " + serverpath + "/fbtest.xpi")

# If firefox is running, kill it (needed for mozrunner)
kill_firefox()

sleep(2)

subprocess.Popen(shlex.split("mozrunner -n -p " + profile + " --addons=\"./firebug.xpi\",\"./fbtest.xpi\""))
os.system("firefox -runFBTests " + serverpath + "/tests/content/testlists/firebug" + firebug_version + ".html")# -P " + profile)

# Cleanup
os.system("rm ./firebug.xpi")
os.system("rm ./fbtest.xpi")
kill_firefox()
sys.exit(0)