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

from optparse import OptionParser
from ConfigParser import ConfigParser
import os, sys
import mozrunner
import fb_logs
import fb_utils as utils
import platform

class FBRunner:
    def __init__(self, **kwargs): 
        # Initialization  
        self.binary = kwargs["binary"]
        self.profile = kwargs["profile"]
        self.serverpath = kwargs["serverpath"]
        self.version = kwargs["version"]
        self.couchURI = kwargs["couchURI"]
        self.databasename = kwargs["databasename"]
        self.testlist = kwargs["testlist"]
        self.platform = platform.system().lower()

    def cleanup(self):
        """
        Remove temporarily downloaded files
        """
        try:
            "Perform cleanup and exit"
            if os.path.exists("firebug.xpi"):
                os.remove("firebug.xpi")
            if os.path.exists("fbtest.xpi"):
                os.remove("fbtest.xpi")
            if os.path.exists("test-bot.config"):
                os.remove("test-bot.config")
        except Exception as e:
            print "[Warn] Could not clean up temporary files: " + str(e)        
        
    def get_extensions(self):
        """
        Downloads the firebug and fbtest extensions
        for the specified Firebug version
        """
        utils.download(self.serverpath + "releases/firebug/test-bot.config", "test-bot.config")
        config = ConfigParser()
        config.read("test-bot.config")
        FIREBUG_XPI = config.get("Firebug" + self.version, "FIREBUG_XPI")
        FBTEST_XPI = config.get("Firebug" + self.version, "FBTEST_XPI")
        os.remove("test-bot.config")
        utils.download(FIREBUG_XPI, "firebug.xpi")
        utils.download(FBTEST_XPI, "fbtest.xpi")

    def disable_compatibility_check(self):
        """
        Disables compatibility check which could
        potentially prompt the user for action
        """
        try:
            app = ConfigParser()
            app.read(os.path.join(os.path.dirname(self.binary), "application.ini"))
            ver = app.get("App", "Version")
            index = max(ver.find('a'), ver.find('b'))
            if index > -1:
                ver = ver[:index]

            prefs = open(os.path.join(self.profile, "prefs.js"), "a")
            prefs.write("user_pref(\"extensions.checkCompatibility." + ver + "\", false);\n")
            prefs.write("user_pref(\"extensions.checkCompatibility." + ver + "a\", false);\n")
            prefs.write("user_pref(\"extensions.checkCompatibility." + ver + "b\", false);\n")
            prefs.close();
        except Exception as e:
            print "[Warn] Could not disable compatibility check: " + str(e)
        
    def run(self):
        """
        Code for running the tests
        """
        if self.profile:
            # Ensure the profile actually exists
            if not os.path.exists(os.path.join(self.profile, "prefs.js")):
                print "[Warn] Profile '" + self.profile + "' doesn't exist.  Creating temporary profile"
                self.profile = None
            else:
                # Move any potential existing log files to log_old folder
                for name in os.listdir(os.path.join(self.profile, "firebug/fbtest/logs")):
                    os.rename(os.path.join(self.profile, "firebug/fbtest/logs", name), os.path.join(self.profile, "firebug/fbtest/logs_old", name))

        # Ensure serverpath has correct format
        self.serverpath = self.serverpath.rstrip("/") + "/"
        
        # Ensure we have a testlist set
        if not self.testlist:
            self.testlist = self.serverpath + "tests/content/testlists/firebug" + self.version + ".html"

        # If extensions were left over from last time, delete them
        self.cleanup()

        # Grab the extensions from server   
        try:
            self.get_extensions()
        except Exception as e:
            self.cleanup()
            print "[Error] Extensions could not be downloaded: " + str(e)
            return

        # Create environment variables
        dict = os.environ
        dict["XPC_DEBUG_WARN"] = "warn"     # Suppresses certain alert warnings that may sometimes appear

        # If firefox is running, kill it (needed for mozrunner)
        mozrunner.kill_process_by_name("firefox" + (".exe" if self.platform == "windows" else "-bin"))

        # Create profile for mozrunner and start the Firebug tests
        print "[Info] Starting FBTests"
        try:
            profile = mozrunner.FirefoxProfile(profile=self.profile, addons=["firebug.xpi", "fbtest.xpi"])
            self.profile = profile.profile
                    
            # Disable the compatibility check on startup
            self.disable_compatibility_check()
            
            runner = mozrunner.FirefoxRunner(binary=self.binary, profile=profile, 
                                             cmdargs=["-runFBTests", self.testlist], env=dict)
            runner.start()
        except Exception as e:
            self.cleanup()
            print "[Error] Could not start Firefox: " + str(e)
            return

        # Find the log file
        timeout, logfile = 0, 0
        # Wait up to 5 minutes for the log file to be initialized
        while not logfile and timeout < 300:
            try:
                for name in os.listdir(os.path.join(self.profile, "firebug/fbtest/logs")):
                    logfile = open(os.path.join(self.profile, "firebug/fbtest/logs/", name))
            except OSError:
                timeout += 1
                mozrunner.sleep(1)
                
        # If log file was not found, create our own log file
        if not logfile:
            print "[Error] Could not find the log file in profile '" + self.profile + "'"
            logfile = utils.create_log(self.profile, self.binary, self.testlist)
        # If log file found, exit when fbtests finished (if no activity, wait up to 10 min)
        else:
            line, timeout = "", 0
            while line.find("Test Suite Finished") == -1 and timeout < 600:
                line = logfile.readline()
                if line == "":
                    mozrunner.sleep(1)
                    timeout += 1
                else:
                    timeout = 0
                    
        # Give last two lines of file a chance to write and send log file to fb_logs  
        mozrunner.sleep(2)
        filename = logfile.name
        logfile.close()
        print "[Info] Sending log file to couchdb at '" + self.couchURI + "'"
        try:
            fb_logs.main(["--log", filename, "--database", self.databasename, "--couch", self.couchURI,
                             "--changeset", utils.get_changeset((self.binary if self.platform == "darwin" else os.path.dirname(self.binary)))])
        except Exception as e:
            print "[Error] Log file not sent to couchdb at server: '" + self.couchURI + "' and database: '" + self.databasename + "': " + str(e)
            
        # Cleanup
        mozrunner.kill_process_by_name("crashreporter" + (".exe" if self.platform == "windows" else ""))
        mozrunner.kill_process_by_name("firefox" + (".exe" if self.platform == "windows" else "-bin"))
        self.cleanup()


# Called from the command line
def cli(argv=sys.argv[1:]):
    parser = OptionParser("usage: %prog [options]")
    parser.add_option("-b", "--binary", dest="binary",
                      help="Firefox binary path")
                    
    parser.add_option("-p", "--profile", dest="profile",
                      help="The profile to use when running Firefox")
                        
    parser.add_option("-s", "--serverpath", dest="serverpath", 
                      default="https://getfirebug.com",
                      help="The http server containing the firebug tests")
                        
    parser.add_option("-v", "--version", dest="version",
                      default="1.6",
                      help="The firebug version to run")
                        
    parser.add_option("-c", "--couch", dest="couchURI",
                      default="http://localhost:5984",
                      help="URI to couchdb server for log information")
                        
    parser.add_option("-d", "--database", dest="databasename",
                      default="firebug",
                      help="Database name to keep log information")
                        
    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Specify the name of the testlist to use, should usually use the default")
    (opt, remainder) = parser.parse_args(argv)
    
    runner = FBRunner(binary=opt.binary, profile=opt.profile, serverpath=opt.serverpath, version=opt.version, 
                                        couchURI=opt.couchURI, databasename=opt.databasename, testlist=opt.testlist)
    runner.run()
    
if __name__ == '__main__':
    cli()
