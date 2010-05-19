from ConfigParser import ConfigParser
from time import sleep
import os, sys, signal, subprocess, shlex, getopt, mozrunner

def ping_firefox():
    "See if Firefox is still running"
    for line in os.popen("ps xa"):
        fields = line.split()
        pid = fields[0]
        process = fields[4]
        if process.find("firefox-bin") > 0 and process.find("<defunct>") == -1:
            return pid
    return 0

def kill_firefox():
    "Kill Firefox if it is running"
    pid = ping_firefox()
    if pid > 0:
        os.kill(int(pid), signal.SIGHUP)

def cleanup(exit_code):
    "Perform cleanup and exit"
    os.system("rm ./firebug.xpi")
    os.system("rm ./fbtest.xpi")
    sys.exit(exit_code)

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

if profile.lower() == "auto":
    # Attempt to find the default profile automatically
    p = subprocess.Popen("locate -r \\\\.mozilla/firefox.*\\\\.default$", shell=True, stdout=subprocess.PIPE)
    try:
        profile = p.communicate()[0]
    except IndexError:
        pass
    
print profile
profile = str(profile[:-1])
#print profile
if not os.path.exists(profile):#"/home/mozilla/.mozilla/firefox/ty98qut7.default"):
    #print "[Error] Profile doesn't exist: " + profile
    cleanup(1)

# Move existing log files to log_old folder (hidden)
os.system("mv " + profile + "/firebug/fbtest/logs/* " + profile + "/firebug/fbtest/logs_old/")

# If firefox is running, kill it (needed for mozrunner)
kill_firefox()
sleep(2)
# Install the two extensions using mozrunner
subprocess.Popen(shlex.split("mozrunner -n -p " + profile + " --addons=\"./firebug.xpi\",\"./fbtest.xpi\""))
sleep(5)
# Run Firefox with -runFBTests command line option
subprocess.Popen("firefox -runFBTests " + serverpath + "/tests/content/testlists/firebug" + firebug_version + ".html", shell=True)
sleep(2)

# Find the 
for name in os.listdir(profile + "/firebug/fbtest/logs"):
    file = open(profile + "/firebug/fbtest/logs/" + name)

# Send the log file to stdout as it arrives
while ping_firefox():
    line = file.readline()
    if (line != ""):
        print line[:-1]


# Cleanup
cleanup(0)

