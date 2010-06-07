from ConfigParser import ConfigParser
from optparse import OptionParser
import os, sys, mozrunner, urllib2, fb_logs

def cleanup():
    "Perform cleanup and exit"
    if os.path.exists("firebug.xpi"):
        os.remove("firebug.xpi")
    if os.path.exists("fbtest.xpi"):
        os.remove("fbtest.xpi")
        
def retrieve_url(url, filename):
    ret = urllib2.urlopen(url)
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()

def main(argv): 
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
    parser.add_option("-c", "--couch", dest="couchserveruri", default=config.get("log", "couch_server"), help="URI to couchdb server for log information")
    parser.add_option("-d", "--database", dest="databasename", default=config.get("log", "database_name"), help="Database name to keep log information")
    (opt, remainder) = parser.parse_args(argv)

    if opt.profile != None:
        # Ensure the profile actually exists
        if not os.path.exists(os.path.join(opt.profile, "prefs.js")):
            print "[Warn] Profile '" + opt.profile + "' doesn't exist.  Creating temporary profile"
            opt.profile = None
        else:
            pass
            # Move any potential existing log files to log_old folder
            for name in os.listdir(os.path.join(opt.profile, "firebug/fbtest/logs")):
                os.rename(os.path.join(opt.profile, "firebug/fbtest/logs", name), os.path.join(opt.profile, "firebug/fbtest/logs_old", name))

    # Concatenate serverpath based on Firebug version
    opt.serverpath = opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "firebug" + opt.version

    print opt.serverpath

    # If the extensions were somehow left over from last time, delete them to ensure we don't accidentally run the wrong version
    cleanup()

    # Grab the extensions from the server   
    retrieve_url(opt.serverpath + "/firebug.xpi", "firebug.xpi")
    retrieve_url(opt.serverpath + "/fbtest.xpi", "fbtest.xpi")

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

    # Find the log file
    timeout, file = 0, 0
    # Wait up to a minute for the log file to be initialized
    while not file and timeout < 60:
        try:
            for name in os.listdir(os.path.join(profile.profile, "firebug/fbtest/logs")):
                file = open(os.path.join(profile.profile, "firebug/fbtest/logs/", name))
        except OSError:
            timeout += 1
            mozrunner.sleep(1)
    if not file:
        print "[Error] Could not find the log file"
        cleanup()
        sys.exit(1)


    # Send the log file to stdout as it arrives, exit when firefox process is no longer running (i.e fbtests are finished)
    while len(mozrunner.get_pids("firefox")) > 0:
        mozrunner.sleep(1)
    
    print file.name
    fb_logs.main(["--log", file.name, "--database", opt.databasename, "--couch", opt.couchserveruri])    
    
## This will be needed for buildbot integration later on
##        line = file.readline()
##        if (line != ""):
##            print line[:-1]
##        else:
##            mozrunner.sleep(1)
##            
##    # Ensure we have retrieved the entire log file
##    line = file.readline()
##    while line != "":
##        print line[:-1]
##        line = file.readline()
        
    # Cleanup
    file.close()
    cleanup()
    
if __name__ == '__main__':
    main(sys.argv[1:])