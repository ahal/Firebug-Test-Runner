from ConfigParser import ConfigParser
from optparse import OptionParser
import os, sys, subprocess, mozrunner, httplib

def cleanup():
    "Perform cleanup and exit"
    if os.path.exists("firebug.xpi"):
        subprocess.call("rm firebug.xpi", shell=True)
    if os.path.exists("fbtest.xpi"):
        subprocess.call("rm fbtest.xpi", shell=True)

# Initialization
config = ConfigParser()
try:
    config.read("fb-test-runner.config")
except ConfigParser.NoSectionError:
    print "[Error] Could not find 'fb-test-runner.config'"
    sys.exit(1)

parser = OptionParser("usage: %prog [options]")
parser.add_option("-b", "--binary", dest="binary", help="Firefox binary path")
parser.add_option("-p", "--profile", dest="profile", help="The profile to use when running Firefox")
parser.add_option("-s", "--serverpath", dest="serverpath", default=config.get("run", "serverpath"), help="The http server containing the fb tests")
parser.add_option("-v", "--version", dest="version", default=config.get("run", "firebug_version"), help="The firebug version to run")
(opt, remainder) = parser.parse_args()

if opt.profile != None:
    # Ensure the profile actually exists
    if not os.path.exists(os.path.join(opt.profile, "prefs.js")):
        print "[Warn] Profile '" + opt.profile + "' doesn't exist.  Creating temporary profile"
        opt.profile = None
    else:
        # Move any potential existing log files to log_old folder
        subprocess.call("mv " + os.path.join(opt.profile, "firebug/fbtest/logs/*") + " " + os.path.join(opt.profile, "firebug/fbtest/logs_old"), shell=True)

# Concatenate serverpath based on Firebug version
opt.serverpath = os.path.join(opt.serverpath, "firebug" + opt.version)

# If the extensions were somehow left over from last time, delete them to ensure we don't accidentally run the wrong version
cleanup()

# Grab the extensions from the server   
subprocess.call("wget -N " + os.path.join(opt.serverpath, "firebug.xpi") + " " + os.path.join(opt.serverpath, "fbtest.xpi"), shell=True)

# Ensure the extensions were downloaded properly, exit if not
if not os.path.exists("firebug.xpi") or not os.path.exists("fbtest.xpi"):
    print "[Error] Extensions could not be downloaded. Check that '" + opt.serverpath + "' exists and run 'fb-update.py' on the host machine"
    sys.exit(1)

# If firefox is running, kill it (needed for mozrunner)
mozrunner.kill_process_by_name("firefox-bin")

# Create profile for mozrunner and start the Firebug tests
profile = mozrunner.FirefoxProfile(profile=opt.profile, create_new=(True if opt.profile==None else False), addons=["firebug.xpi", "fbtest.xpi"])
runner = mozrunner.FirefoxRunner(binary=opt.binary, profile=profile, cmdargs=["-runFBTests", os.path.join(opt.serverpath, "tests/content/testlists/firebug" + opt.version + ".html")])
runner.start()

mozrunner.sleep(5)

print os.path.join(profile.profile, "firebug/fbtest/logs")

# Find the log file
for name in os.listdir(os.path.join(profile.profile, "firebug/fbtest/logs")):
    file = open(os.path.join(profile.profile, "firebug/fbtest/logs/", name))

# Send the log file to stdout as it arrives, exit when firefox process is no longer running (i.e fbtests are finished)
while len(mozrunner.get_pids("firefox")) > 0:
    line = file.readline()
    if (line != ""):
        print line[:-1]
    else:
        mozrunner.sleep(1)
        
# Ensure we have retrieved the entire log file
line = file.readline()
while line != "":
    print line[:-1]
    line = file.readline()
    
# Cleanup
cleanup()