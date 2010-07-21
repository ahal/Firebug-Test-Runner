#!/usr/bin/python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is the Firebug Test Runner.
#
# The Initial Developer of the Original Code is
# Andrew Halberstadt.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Andrew Halberstadt - ahalberstadt@mozilla.com
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

from ConfigParser import ConfigParser
from optparse import OptionParser
import os, sys, mozrunner, urllib2, fb_logs, datetime

def cleanup():
    "Perform cleanup and exit"
    if os.path.exists("firebug.xpi"):
        os.remove("firebug.xpi")
    if os.path.exists("fbtest.xpi"):
        os.remove("fbtest.xpi")
    if os.path.exists("test-bot.config"):
        os.remove("test-bot.config")
        
def retrieve_url(url, filename):
    try:    
        ret = urllib2.urlopen(url)
    except:
        return -1
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()
    return 0

def parse_rdf(lines, tagname):
    for line in lines:
        if line.find("<em:" + tagname + ">") != -1:
            return line[line.find(">") + 1:line.rfind("<")]
    return -1

def create_log(profile, opt):
    try:
        content = []
        file = open(os.path.join(profile, "extensions/firebug@software.joehewitt.com/install.rdf"))
        content.append("FIREBUG INFO | Firebug: " + parse_rdf(file.readlines(), "version") + "\n")
        file = open(os.path.join(profile, "extensions/fbtest@mozilla.com/install.rdf"))
        content.append("FIREBUG INFO | FBTest: " + parse_rdf(file.readlines(), "version") + "\n")
        parser = ConfigParser()
        parser.read(os.path.join(opt.binary[0:opt.binary.rfind("/") if opt.binary.rfind("/") != -1 else opt.binary.rfind("\\")], "application.ini"))
        content.append("FIREBUG INFO | App Name: " + parser.get("App", "Name") + "\n")
        content.append("FIREBUG INFO | App Version: " + parser.get("App", "Version") + "\n")
        content.append("FIREBUG INFO | App Platform: " + parser.get("Gecko", "MaxVersion") + "\n")
        content.append("FIREBUG INFO | App BuildID: " + parser.get("App", "BuildID") + "\n")
        content.append("FIREBUG INFO | Export Date: " + datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT") + "\n")
        content.append("FIREBUG INFO | Test Suite: " + opt.serverpath + "/tests/content/testlists/" + opt.testlist + "\n")
        content.append("FIREBUG INFO | Total Tests: 0\n")
        content.append("FIREBUG INFO | Fail | [START] Could not start FBTests\n")
        file = open(os.path.join(profile, "firebug/firebug-test.log"), "w")        
        file.writelines(content)
        return file
    except:
        return -1
    
def disable_crashreporter(binary_path):
    print binary_path
    try:    
        parser = ConfigParser()
        parser.read(os.path.join(binary_path, "application.ini"))
        if parser.has_option("Crash Reporter", "Enabled"):
            parser.set("Crash Reporter", "Enabled", 0)
            file = open(os.path.join(binary_path, "application.ini"), "w")
            parser.write(file)
            file.close()
            return 0
    except:
        pass
    return -1
    
def run_test(opt):
    if opt.testlist == None:
        opt.testlist = "firebug" + opt.version + ".html"

    if opt.profile != None:
        # Ensure the profile actually exists
        if not os.path.exists(os.path.join(opt.profile, "prefs.js")):
            print "[Warn] Profile '" + opt.profile + "' doesn't exist.  Creating temporary profile"
            opt.profile = None
        else:
            # Move any potential existing log files to log_old folder
            for name in os.listdir(os.path.join(opt.profile, "firebug/fbtest/logs")):
                os.rename(os.path.join(opt.profile, "firebug/fbtest/logs", name), os.path.join(opt.profile, "firebug/fbtest/logs_old", name))

    # Concatenate serverpath based on Firebug version
    opt.serverpath = opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "firebug" + opt.version

    # If the extensions were somehow left over from last time, delete them to ensure we don't accidentally run the wrong version
    cleanup()

    # Grab the extensions from the server   
    if retrieve_url(opt.serverpath + "/firebug.xpi", "firebug.xpi") != 0 or retrieve_url(opt.serverpath + "/fbtest.xpi", "fbtest.xpi") != 0:
        return "[Error] Extensions could not be downloaded. Check that '" + opt.serverpath + "' exists and run 'fb-update.py' on the host machine"

    # If firefox is running, kill it (needed for mozrunner)
    mozrunner.kill_process_by_name("firefox-bin")

    # Create environment variables
    dict = os.environ
    dict["XPC_DEBUG_WARN"] = "warn"

    # Disable crash reporter
    if disable_crashreporter(opt.binary[0:opt.binary.rfind("/") if opt.binary.rfind("/") != -1 else opt.binary.rfind("\\")]) != 0:
        print "[Warn] Could not disable crash reporter"

    # Create profile for mozrunner and start the Firebug tests
    print "[Info] Starting FBTests"
    try:
        profile = mozrunner.FirefoxProfile(profile=opt.profile, create_new=(True if opt.profile==None else False),
                                           addons=["firebug.xpi", "fbtest.xpi"])
                                        
        runner = mozrunner.FirefoxRunner(binary=opt.binary, profile=profile, 
                                         cmdargs=["-runFBTests", opt.serverpath + "/tests/content/testlists/" + opt.testlist], env=dict)
        runner.start()
    except IOError:
        cleanup()
        return "[Error] Could not download the firebug extensions"

    # Find the log file
    timeout, file = 0, 0
    # Wait up to 5 minutes for the log file to be initialized
    while not file and timeout < 300:
        try:
            for name in os.listdir(os.path.join(profile.profile, "firebug/fbtest/logs")):
                file = open(os.path.join(profile.profile, "firebug/fbtest/logs/", name))
        except OSError:
            timeout += 1
            mozrunner.sleep(1)
            
    # If log file was not found, create our own log file
    if not file:
        print "[Error] Could not find the log file in profile '" + profile.profile + "'"
        file = create_log(profile.profile, opt)
    # If log file was found, exit when fbtests are finished (wait up to 30 min)
    else:
        line, timeout = "", 0
        while line.find("Test Suite Finished") == -1 and timeout < 1800:
            line = file.readline()
            if line == "":
                mozrunner.sleep(1)
                timeout += 1;
                
    # Give last two lines of file a chance to write and send log file to fb_logs.py  
    if file != -1:
        mozrunner.sleep(2)
        filename = file.name
        file.close()
        print "[Info] Sending log file to couchdb at '" + opt.couchserveruri + "'"
        if fb_logs.main(["--log", filename, "--database", opt.databasename, "--couch", opt.couchserveruri, "--changeset", opt.changeset]) != 0:
            return "[Error] Log file not sent to couchdb at server: '" + opt.couchserveruri + "' and database: '" + opt.databasename + "'" 
        
    # Cleanup
    mozrunner.kill_process_by_name("firefox-bin")
    cleanup()
    return 0

def main(argv): 
    # Initialization
    config = ConfigParser()
    try:
        config.read("fb-test-runner.config")
    except ConfigParser.NoSectionError:
        print "[Warn] Could not find 'fb-test-runner.config' in local directory"
        file = open("fb-test-runner.config", "w")
        file.close()
        config.read("fb-test-runner.config")

    parser = OptionParser("usage: %prog [options]")
    parser.add_option("-b", "--binary", dest="binary", 
                      help="Firefox binary path")
                    
    parser.add_option("-p", "--profile", dest="profile", 
                      help="The profile to use when running Firefox")
                        
    parser.add_option("-s", "--serverpath", dest="serverpath", 
                      default=config.get("run", "serverpath"),
                      help="The http server containing the fb tests")
                        
    parser.add_option("-v", "--version", dest="version",
                      default=config.get("run", "firebug_version"),
                      help="The firebug version to run")
                        
    parser.add_option("-c", "--couch", dest="couchserveruri",
                      default=config.get("log", "couch_server"),
                      help="URI to couchdb server for log information")
                        
    parser.add_option("-d", "--database", dest="databasename",
                      default=config.get("log", "database_name"),
                      help="Database name to keep log information")
                        
    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Specify the name of the testlist to use, should usually use the default")
                        
    parser.add_option("--changeset", dest="changeset")
    (opt, remainder) = parser.parse_args(argv)
    
    print opt.binary
    # Disable crash reporter
    if disable_crashreporter(opt.binary[0:opt.binary.rfind("/") if opt.binary.rfind("/") != -1 else opt.binary.rfind("\\")]) != 0:
        print "[Warn] Could not disable crash reporter"

    sys.exit(0)
    return run_test(opt)


    
if __name__ == '__main__':
    main(sys.argv[1:])
