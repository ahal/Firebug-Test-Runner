from ConfigParser import ConfigParser
from time import sleep
import os, sys, signal, subprocess, shlex, getopt

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
try:
    config.read("./fb-test-runner.config")
except ConfigParser.NoSectionError:
    print "[Error] Could not find 'fb-test-runner.config'"
    sys.exit(1)
    
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
        assert False, "Unhandled command line option"

if config.get("run", "auto_profile").lower() == "on":
    # Attempt to find the default profile automatically
    p = subprocess.Popen("locate -r \\\\.mozilla/firefox.*\\\\.default$", shell=True, stdout=subprocess.PIPE)
    try:
        profile = p.communicate()[0]
        profile = str(profile[:-1])
    except IndexError:
        print "[Warn] Could not find default profile automatically, using profile '" + profile + "' instead"

# Ensure the profile actually exists
if not os.path.exists(profile + "/prefs.js"):
    print "[Error] Profile doesn't exist: " + profile
    sys.exit(1)

# Concatenate serverpath based on Firebug version
if serverpath[-1:] != "/":
    serverpath = serverpath + "/firebug" + firebug_version
else:
    serverpath = serverpath + "firebug" + firebug_version
# If the extensions were somehow left over from last time, delete them to ensure we don't accidentally run
if os.path.exists("./firebug.xpi"):
    os.system("rm ./firebug.xpi")
if os.path.exists("./fbtest.xpi"):
    os.system("rm ./fbtest.xpi")
# Grab the extensions from the server
os.system("wget -N " + serverpath + "/firebug.xpi " + serverpath + "/fbtest.xpi")
# Ensure the extensions were downloaded properly, exit if not
if not os.path.exists("./firebug.xpi") or not os.path.exists("./fbtest.xpi"):
    print "[Error] Extensions could not be downloaded. Check that '" + serverpath + "' exists and run 'fb-update.py'"
    sys.exit(1)

# Move existing log files to log_old folder (hidden)
os.system("mv " + profile + "/firebug/fbtest/logs/* " + profile + "/firebug/fbtest/logs_old/")

# If firefox is running, kill it (needed for mozrunner)
kill_firefox()
sleep(2)
# Install the two extensions using mozrunner
subprocess.Popen(shlex.split("mozrunner -n -p " + profile + " --addons=\"./firebug.xpi\",\"./fbtest.xpi\""))
sleep(5)
# Run Firefox with -runFBTests command line option (has to be run from shell otherwise log file won't be created)
subprocess.Popen("firefox -runFBTests " + serverpath + "/tests/content/testlists/firebug" + firebug_version + ".html", shell=True)
sleep(2)

# Find the log file
for name in os.listdir(profile + "/firebug/fbtest/logs"):
    file = open(profile + "/firebug/fbtest/logs/" + name)

# Send the log file to stdout as it arrives, exit when firefox process is no longer running (i.e fbtests are finished)
while ping_firefox():
    line = file.readline()
    if (line != ""):
        print line[:-1]
    else:
        sleep(1)
        
# Ensure we have retrieved the entire log file
line = file.readline()
while line != "":
    print line[:-1]

# Cleanup
cleanup(0)