from ConfigParser import ConfigParser
from time import sleep
import os, sys, signal, subprocess, shlex, getopt, mozrunner


def kill_firefox():
    for line in os.popen("ps xa"):
        fields = line.split()
        pid = fields[0]
        process = fields[4]
        if process.find("firefox-bin") > 0 and process.find("<defunct>") == -1:
            os.kill(int(pid), signal.SIGHUP)
            break
        
def ping_firefox():
    for line in os.popen("ps xa"):
        fields = line.split()
        pid = fields[0]
        process = fields[4]
        if process.find("firefox-bin") > 0 and process.find("<defunct>") == -1:
            return 1
    return 0

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

if serverpath[-1:] != "/":
    serverpath = serverpath + "/firebug" + firebug_version
else:
    serverpath = serverpath + "firebug" + firebug_version

# Grab the extensions
os.system("wget -N " + serverpath + "/firebug.xpi " + serverpath + "/fbtest.xpi")

# If firefox is running, kill it (needed for mozrunner)
kill_firefox()

sleep(2)

subprocess.Popen(shlex.split("mozrunner -n -p " + profile + " --addons=\"./firebug.xpi\",\"./fbtest.xpi\""))
sleep(5)
subprocess.Popen("firefox -runFBTests " + serverpath + "/tests/content/testlists/firebug" + firebug_version + ".html", shell=True)

count = 0
while ping_firefox():
    sleep(1)
    count += 1
    if count % 30 == 0:
        print "I'm not dead yet!"


# Cleanup
os.system("rm ./firebug.xpi")
os.system("rm ./fbtest.xpi")
sys.exit(0)

