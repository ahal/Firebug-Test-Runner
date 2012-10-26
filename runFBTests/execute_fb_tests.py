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

from time import sleep
from ConfigParser import ConfigParser
import fb_run
import fb_utils as utils
import os, sys, shutil
import optparse
import subprocess
import tempfile
import platform
import traceback
import mozlog

if platform.system().lower() == "windows":
    import zipfile
else:
    import tarfile

class FBWrapper:
    def __init__(self, **kwargs):
        # Set up the log file or use stdout if none specified
        self.log = mozlog.getLogger('FIREBUG', kwargs.get('log'))
        self.log.setLevel(mozlog.DEBUG if kwargs.get('debug') else mozlog.INFO)

        # Initialization
        self.binary = kwargs.get("binary")
        self.profile = kwargs.get("profile")
        self.serverpath = kwargs.get("serverpath")
        self.couchURI = kwargs.get("couchURI")
        self.databasename = kwargs.get("databasename")
        self.testlist = kwargs.get("testlist")
        self.waitTime = kwargs.get("waitTime")
        self.debug = kwargs.get("debug")
        self.platform = platform.system().lower()

        self.tempdir = tempfile.gettempdir();                               # Temporary directory to store tinderbox builds and temporary profiles
        self.serverpath = self.serverpath.rstrip("/") + "/"                 # Ensure serverpath has correct format
        self.changeset = {}                                                 # Map to keep track of the last changeset of each build that was run (to prevent running twice on the same changeset)

    def clean_temp_folder(self, build=False):
        """
        Clean the temporary directory
        """
        try:
            if build:
                if self.platform != "darwin":
                    bundle = os.path.join(self.tempdir, "mozilla-" + build + (".zip" if self.platform == "windows" else ".tar.bz2"))
                    if os.path.isfile(bundle):
                        os.remove(bundle)
                if os.path.isdir(os.path.join(self.tempdir, "mozilla-" + build)):
                    shutil.rmtree(os.path.join(self.tempdir, "mozilla-" + build))
            for filename in os.listdir(self.tempdir):
                if os.path.isdir(os.path.join(self.tempdir, filename)) and filename[0:3] == "tmp":
                    shutil.rmtree(os.path.join(self.tempdir, filename))
        except Exception, e:
            self.log.warn("Could not delete temporary files in '" + self.tempdir)
            self.log.warn(traceback.format_exc())

    def build_needed(self, section, build, buildpath):
        """
        Return True if the tests have never been run against the current changeset of 'build'
        Return False otherwise
        """
        if self.platform == 'darwin':
            buildpath = os.path.join(buildpath, 'Contents', 'MacOS')
        # Find new changeset
        new_changeset = utils.get_changeset(buildpath)
        if not (section, build) in self.changeset:
            self.changeset[(section, build)] = -1
        if self.changeset[(section, build)] != new_changeset:
            self.changeset[(section, build)] = new_changeset
            return True
        return False

    def start_tests(self, section):
        """
        Start the tests by invoking fb_run
        """
        runner = fb_run.FBRunner(binary=self.binary, profile=self.profile, serverpath=self.serverpath, debug=self.debug,
                                                        section=section, couchURI=self.couchURI, databasename=self.databasename, testlist=self.testlist)
        runner.run()


    def prepare_builds(self, section, builds):
        """
        Downloads the builds and starts the tests
        """
        # For each version of Firefox, see if there is a new changeset and run the tests
        for build in builds:
            # put this here because the firebug team sometimes forgets and puts 'mozilla-central' instead of central
            if build.lower() == "mozilla-central":
                build = "central";

            self.log.info("Running " + section + " tests against Mozilla " + build)

            # Scrape for the latest tinderbox build and extract it to the basedir
            try:
                # Location to save the tinderbox build
                buildPath = os.path.join(self.tempdir, "mozilla-" + build);

                # Get the url to the latest tinderbox build
                proc = subprocess.Popen("get-latest-tinderbox --product=mozilla-" + build, shell=True, stdout=subprocess.PIPE)
                tinderbox_url = proc.communicate()[0]

                # Download and extract the tinderbox build
                if self.platform == "darwin":
                    utils.download(tinderbox_url, os.path.join(buildPath, "firefox.dmg"))
                    proc = subprocess.Popen("hdiutil mount " + os.path.join(buildPath,  "firefox.dmg"), shell=True, stdout=subprocess.PIPE)
                    for data in proc.communicate()[0].split():
                        if data.find("/Volumes/") != -1:
                            appDir = data
                    for appFile in os.listdir(appDir):
                        if appFile[-4:] == ".app":
                            appName = appFile
                            break
                    subprocess.call("cp -r " + os.path.join(appDir, appName) + " " + buildPath, shell=True)
                    subprocess.call("hdiutil detach " + appDir, shell=True)
                    buildPath = os.path.join(buildPath, appName)
                else:
                    if self.platform == "windows":
                        utils.download(tinderbox_url, buildPath + ".zip")
                        bundle = zipfile.ZipFile(buildPath + ".zip")
                    else:
                        utils.download(tinderbox_url, buildPath + ".tar.bz2")
                        bundle = tarfile.open(buildPath + ".tar.bz2")
                    bundle.extractall(buildPath)
                    bundle.close()
                    buildPath = os.path.join(buildPath, "firefox")
            except Exception:
                self.log.error("Could not prepare the latest tinderbox build")
                self.log.error(traceback.format_exc())
                continue

            # If the newest tinderbox changeset is different from the previously run changeset
            if self.build_needed(section, build, buildPath):
                if self.platform == "darwin":
                    self.binary = buildPath
                else:
                    self.binary = os.path.join(buildPath, "firefox" + (".exe" if self.platform == "windows" else ""))
                try:
                    self.start_tests(section)
                except Exception:
                    self.log.error("Running " + section + " against Mozilla " + build + " failed")
                    self.log.error(traceback.format_exc())
                self.binary = None
            else:
                self.log.info("Tests already run with this changeset")

            # Remove build directories and temp files
            self.clean_temp_folder(build)

        self.testlist = None
        return 0

    def run(self):
        """
        Module initialization and loop
        """
        while True:
            try:
                # Download test-bot.config to see which versions of Firefox to run the FBTests against
                utils.download("%sreleases/firebug/test-bot.config" % self.serverpath, "test-bot.config")
                config = ConfigParser()
                config.read("test-bot.config")

                for section in config.sections():
                    try:
                        if not self.testlist:
                            self.testlist = config.get(section, "TEST_LIST")
                        if not self.binary:
                            builds = config.get(section, "GECKO_VERSION").split(",")
                    except Exception:
                        self.log.error("Could not parse config file")
                        self.log.error(traceback.format_exc())
                        continue

                    self.log.info("Starting builds and FBTests for %s" % section)
                    # Run the build(s)
                    if not self.binary:
                        ret = self.prepare_builds(section, builds)
                        if ret != 0:
                            self.log.error(ret)
                    else:
                        self.start_tests(section)

                    self.clean_temp_folder()

            except Exception:
                self.log.error("Could not run the FBTests")
                self.log.error(traceback.format_exc())
                raise

            if not self.waitTime:
                mozlog.shutdown()
                break;

            # Wait for specified number of hours
            self.log.info("Sleeping for %s hour%s" % (self.waitTime, "s" if int(self.waitTime) > 1 else ""))
            sleep(int(self.waitTime) * 3600)

            if os.path.isfile("test-bot.config"):
                os.remove("test-bot.config")


def cli(argv=sys.argv[1:]):
    """
    Called from the command line
    """
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-p", "--profile", dest="profile",
                      help="The profile to use when running Firefox")

    parser.add_option("-b", "--binary", dest="binary",
                      help="The binary path to use. If unspecified appropriate binaries will be downloaded automatically")

    parser.add_option("-s", "--serverpath", dest="serverpath",
                      default="https://getfirebug.com",
                      help="The http server containing the firebug tests")

    parser.add_option("-c", "--couch", dest="couchURI",
                      default="http://localhost:5984",
                      help="URI to couchdb server for log information")

    parser.add_option("-d", "--database", dest="databasename",
                      default="firebug",
                      help="Database name to keep log information")

    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Url to the testlist to use")

    parser.add_option("--interval", dest="waitTime",
                      help="Number of hours to wait between test runs. If unspecified tests are only run once")

    parser.add_option("--debug", dest="debug",
                      action="store_true",
                      help="Enable debug logging")
    (opt, remainder) = parser.parse_args(argv)

    wrapper = FBWrapper(binary=opt.binary, profile=opt.profile, serverpath=opt.serverpath, couchURI=opt.couchURI,
                        databasename=opt.databasename, testlist=opt.testlist, waitTime=opt.waitTime, debug=opt.debug)
    wrapper.run()

if __name__ == '__main__':
     cli()
