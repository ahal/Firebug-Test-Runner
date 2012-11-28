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

from mozrunner import FirefoxRunner
from mozprofile import FirefoxProfile
from optparse import OptionParser
from ConfigParser import ConfigParser, NoOptionError, NoSectionError
from time import sleep
import fb_logs
import fb_utils as utils
import mozlog
import urllib2
import traceback
import os, sys, platform

class FBRunner:
    REMOTE_CONFIG = "releases/firebug/test-bot.config"
    LOCAL_CONFIG = "fb-test-runner.config"

    # Because the only communication between this script and the FBTest console is the
    # log file, we don't know whether there was a crash or the test is just taking awhile.
    # Make 1 minute the timeout for tests.
    TEST_TIMEOUT = 60

    def __init__(self, **kwargs):
        # Set up the log file or use stdout if none specified
        self.log = mozlog.getLogger('FIREBUG', kwargs.get('log'))
        self.log.setLevel(mozlog.DEBUG if kwargs.get('debug') else mozlog.INFO)

        # Initialization
        self.binary = kwargs.get('binary')
        self.profile = kwargs.get('profile')
        self.serverpath = kwargs.get('serverpath')
        self.testlist = kwargs.get('testlist')
        self.couchURI = kwargs.get('couchURI')
        self.databasename = kwargs.get('databasename')
        self.section = kwargs.get('section')
        self.platform = platform.system().lower()

        # Read in fb-test-runner.config for local configuration
        localConfig = ConfigParser()
        localConfig.read(self.LOCAL_CONFIG)
        if not self.serverpath:
            self.serverpath = localConfig.get("runner_args", "server")

        # Ensure serverpath has correct format
        self.serverpath = self.serverpath.rstrip("/") + "/"

        # Get the platform independent app directory and version
        self.appdir, self.appVersion = self.get_app_info()

        # Read in the Firebug team's config file
        try:
            self.download(self.serverpath + self.REMOTE_CONFIG, "test-bot.config")
        except urllib2.URLError:
            self.log.error("Could not download test-bot.config, check that '" + self.serverpath + self.REMOTE_CONFIG + "' is valid")
            self.log.error(traceback.format_exc())
            raise
        self.config = ConfigParser()
        self.config.read("test-bot.config")

        # Make sure we have a testlist
        if not self.testlist:
            try:
                self.testlist = self.config.get(self.section, "TEST_LIST")
            except Exception:
                self.log.error("No testlist specified in config file")
                raise

        if self.config.has_option(self.section, "DB_NAME"):
            self.databasename = self.config.get(self.section, "DB_NAME")

        if self.config.has_option(self.section, "DB_URL"):
            self.couchURI = self.config.get(self.section, "DB_URL")

    def cleanup(self):
        """
        Remove temporarily downloaded files
        """
        try:
            for tmpFile in ["firebug.xpi", "fbtest.xpi", "test-bot.config"]:
                if os.path.exists(tmpFile):
                    self.log.debug("Removing " + tmpFile)
                    os.remove(tmpFile)
        except Exception:
            self.log.warn("Could not clean up temporary files")
            self.log.warn(traceback.format_exc())

    def download(self, url, savepath):
        """
        Save the file located at 'url' into 'filename'
        """
        self.log.debug("Downloading '" + url + "' to '" + savepath + "'")
        ret = urllib2.urlopen(url)
        savedir = os.path.dirname(savepath)
        if savedir and not os.path.exists(savedir):
            os.makedirs(savedir)
        outfile = open(savepath, 'wb')
        outfile.write(ret.read())
        outfile.close()

    def get_app_info(self):
        # Get version of Firefox being run (only possible if we were passed in a binary)
        ver, appdir = None, None
        if self.binary:
            if self.platform == 'darwin':
                appdir = os.path.join(self.binary, 'Contents', 'MacOS')
            else:
                appdir = os.path.dirname(self.binary)
            app = ConfigParser()
            app.read(os.path.join(appdir, "application.ini"))
            ver = app.get("App", "Version").rstrip("0123456789pre")    # Version should be of the form '3.6' or '4.0b' and not the whole string
            ver = ver[:-1] if ver[-1]=="." else ver
        return appdir, ver


    def get_extensions(self):
        """
        Downloads the firebug and fbtest extensions
        for the specified Firebug version
        """
        self.log.debug("Downloading firebug and fbtest extensions from server")
        FIREBUG_XPI = self.config.get(self.section, "FIREBUG_XPI")
        FBTEST_XPI = self.config.get(self.section, "FBTEST_XPI")
        self.download(FIREBUG_XPI, "firebug.xpi")
        self.download(FBTEST_XPI, "fbtest.xpi")

    def disable_compatibility_check(self):
        """
        Disables compatibility check which could
        potentially prompt the user for action
        """
        self.log.debug("Disabling compatibility check")
        try:
            prefs = open(os.path.join(self.profile, "prefs.js"), "a")
            prefs.write("user_pref(\"extensions.checkCompatibility." + self.appVersion + "\", false);\n")
            prefs.close()
        except Exception:
            self.log.warn("Could not disable compatibility check")
            self.log.warn(traceback.format_exc())

    def run(self):
        """
        Code for running the tests
        """
        if self.profile:
            # Ensure the profile actually exists
            if not os.path.exists(self.profile):
                self.log.warn("Profile '" + self.profile + "' doesn't exist.  Creating temporary profile")
                self.profile = None
            else:
                # Move any potential existing log files to log_old folder
                if os.path.exists(os.path.join(self.profile, "firebug", "fbtest", "logs")):
                    self.log.debug("Moving existing log files to archive")
                    for name in os.listdir(os.path.join(self.profile, "firebug", "fbtest", "logs")):
                        os.rename(os.path.join(self.profile, "firebug", "fbtest", "logs", name), os.path.join(self.profile, "firebug", "fbtest", "logs_old", name))

        # Grab the extensions from server
        try:
            self.get_extensions()
        except (NoSectionError, NoOptionError), e:
            self.log.error("Extensions could not be downloaded, malformed test-bot.config")
            self.log.error(traceback.format_exc())
            self.cleanup()
            raise
        except urllib2.URLError, e:
            self.log.error("Extensions could not be downloaded, urllib2 error")
            self.log.error(traceback.format_exc())
            self.cleanup()
            raise

        # Create environment variables
        mozEnv = os.environ
        mozEnv["XPC_DEBUG_WARN"] = "warn"                # Suppresses certain alert warnings that may sometimes appear
        mozEnv["MOZ_CRASHREPORTER_NO_REPORT"] = "true"   # Disable crash reporter UI

        # Create profile for mozrunner and start the Firebug tests
        self.log.info("Starting Firebug Tests")
        try:
            self.log.debug("Creating Firefox profile and installing extensions")
            prefs = {"extensions.update.enabled" : "false"}
            mozProfile = FirefoxProfile(profile=self.profile, addons=["firebug.xpi", "fbtest.xpi"], preferences=prefs)
            self.profile = mozProfile.profile

            self.log.debug("Creating Firefox runner")
            mozRunner = FirefoxRunner(profile=mozProfile, binary=self.binary, cmdargs=["-no-remote", "-runFBTests", self.testlist], env=mozEnv)
            self.binary = mozRunner.binary
            if not self.appVersion:
                self.appdir, self.appVersion = self.get_app_info()

             # Disable the compatibility check on startup
            self.disable_compatibility_check()

            self.log.debug("Running '" + self.binary + " -no-remote -runFBTests " + self.testlist + "'")
            mozRunner.start()
        except Exception:
            self.log.error("Could not start Firefox")
            self.log.error(traceback.format_exc())
            self.cleanup()
            raise

        # Find the log file
        timeout, logfile = 0, 0
        # Wait up to 60 seconds for the log file to be initialized
        while not logfile and timeout < 60:
            try:
                for name in os.listdir(os.path.join(self.profile, "firebug", "fbtest", "logs")):
                    logfile = open(os.path.join(self.profile, "firebug", "fbtest", "logs", name), 'r')
            except Exception:
                timeout += 1
                sleep(1)

        # If log file was not found
        if not logfile:
            self.log.error("Could not find the log file in '" + self.profile + "'")
            self.log.info("This usually indicates the FBTest extension was not started")
            try:
                logfile = utils.create_log(self.profile, self.appdir, self.testlist)
            except Exception:
                self.log.error("Could not synthesize a log file")
                self.log.error(traceback.format_exc())
                self.cleanup()
                raise

        # If log file found, exit when fbtests finished (if no activity, wait up self.TEST_TIMEOUT)
        else:
            line, timeout = "", 0
            while timeout < self.TEST_TIMEOUT:
                line = logfile.readline()
                if line == "":
                    sleep(1)
                    timeout += 1
                else:
                    if line.find("Test Suite Finished") != -1:
                        break
                    timeout = 0
            # If there was a timeout, then there was most likely a crash (however could also be failure in FBTest console or test itself)
            if timeout >= self.TEST_TIMEOUT:
                logfile.seek(1)
                line = logfile.readlines()[-1]
                if line.find("FIREBUG INFO") != -1:
                    line = line[line.find("|") + 1:].lstrip()   # Extract the test name from log line
                    line = line[:line.find("|")].rstrip()
                else:
                    line = "Unknown Test"
                filename = logfile.name
                logfile.close()
                logfile = open(filename, 'a')
                msg = "FIREBUG TEST-UNEXPECTED-FAIL | " + line + " | Possible Firefox crash detected\n"
                logfile.write(msg)       # Print out crash message with offending test
                self.log.warn("Possible crash detected - test run aborted")

        # Give last two lines of file a chance to write and send log file to fb_logs
        sleep(1)
        filename = logfile.name
        logfile.close()

        # Send log file to couchdb
        self.log.info("Sending log file to couchdb at '" + self.couchURI + "'")
        try:
            fb_logs.main(["--log", filename, "--database", self.databasename, "--couch", self.couchURI,
                             "--changeset", utils.get_changeset(self.appdir), "--section", self.section])
        except Exception:
            self.log.error("Log file not sent to couchdb at server: '" + self.couchURI + "' and database: '" + self.databasename)
            self.log.error(traceback.format_exc())

        # Cleanup
        mozRunner.stop()
        self.log.debug("Exiting - Status successful")
        self.cleanup()


# Called from the command line
def cli(argv=sys.argv[1:]):
    parser = OptionParser("usage: %prog [options]")
    parser.add_option("--appname", dest="binary",
                      help="Firefox binary path")

    parser.add_option("--profile-path", dest="profile",
                      help="The profile to use when running Firefox")

    parser.add_option("-s", "--serverpath", dest="serverpath",
                      help="The http server containing the Firebug tests")

    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Name of the testlist to use, should usually use the default")

    parser.add_option("-c", "--couch", dest="couchURI",
                      default="http://localhost:5984",
                      help="URI to couchdb server for log information")

    parser.add_option("-d", "--database", dest="databasename",
                      default="firebug",
                      help="Database name to keep log information")

    parser.add_option("--log", dest="log",
                      help="Path to the log file (default is stdout)")

    parser.add_option("--debug", dest="debug",
                      action="store_true",
                      help="Enable debug logging")
    (opt, remainder) = parser.parse_args(argv)

    try:
        runner = FBRunner(binary=opt.binary, profile=opt.profile, serverpath=opt.serverpath,
                                    testlist=opt.testlist, log=opt.log, debug=opt.debug)
        runner.run()
    except Exception:
        return -1

if __name__ == '__main__':
	sys.exit(cli())
