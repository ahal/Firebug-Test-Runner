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

if platform.system().lower() == "windows":
    import zipfile
else:
    import tarfile

class FBWrapper:
    def __init__(self, **kwargs):
        # Initialization
        self.binary = kwargs["binary"]
        self.profile = kwargs["profile"]
        self.serverpath = kwargs["serverpath"]
        self.version = kwargs["version"]
        self.couchURI = kwargs["couchURI"]
        self.databasename = kwargs["databasename"]
        self.testlist = kwargs["testlist"]
        self.waitTime = kwargs["waitTime"]
        self.platform = platform.system().lower()
        
        self.tempdir = tempfile.gettempdir();                               # Temporary directory to store tinderbox builds and temporary profiles                          
        self.serverpath += ("" if self.serverpath[-1] == "/" else "/")      # Ensure serverpath has correct format
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
        except Exception as e:
            print "[Warn] Could not delete temporary files in '" + self.tempdir + "': " + str(e)

    def build_needed(self, version, build, buildpath):
        """
        Return True if the tests have never been run against the current changeset of 'build'
        Return False otherwise
        """
        # Find new changeset
        new_changeset = utils.get_changeset(buildpath)
        if not (version, build) in self.changeset:
            self.changeset[(version, build)] = -1
        if self.changeset[(version, build)] != new_changeset:
            self.changeset[(version, build)] = new_changeset
            return True
        return False
        
    def start_tests(self, version):
        """
        Start the tests by invoking fb_run
        """
        runner = fb_run.FBRunner(binary=self.binary, profile=self.profile, serverpath=self.serverpath, version=version, 
                                                        couchURI=self.couchURI, databasename=self.databasename, testlist=self.testlist)
        runner.run()
    

    def prepare_builds(self, version, builds):
        """
        Downloads the builds and starts the tests
        """
        # For each version of Firefox, see if there is a new changeset and run the tests
        for build in builds:
            print "[Info] Running Firebug" + version + " tests against Mozilla " + build

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
                    subprocess.call("hdiutil unmount " + appDir, shell=True)
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
            except Exception as e:
                print "[Error] Could not prepare the latest tinderbox build: " + str(e)
                continue
            
            # If the newest tinderbox changeset is different from the previously run changeset
            if self.build_needed(version, build, buildPath):
                if self.platform == "darwin":
                    self.binary = buildPath
                else:
                    self.binary = os.path.join(buildPath, "firefox" + (".exe" if self.platform == "windows" else ""))
                self.start_tests(version)
                self.binary = None
                self.testlist = None
            else:
                print "[Info] Tests already run with this changeset"
                    
            # Remove build directories and temp files
            self.clean_temp_folder(build)
            
        return 0

    def run(self):
        """
        Module initialization and loop
        """
        while True:
            try:
                # Download test-bot.config to see which versions of Firefox to run the FBTests against
                utils.download(self.serverpath + "releases/firebug/test-bot.config", "test-bot.config")
                config = ConfigParser()
                config.read("test-bot.config")
                
                for section in config.sections():
                    version = section[-3:]
                    if not self.version or version == self.version:
                        try:
                            if not self.testlist:
                                self.testlist = config.get("Firebug" + version, "TEST_LIST")
                            if not self.binary:
                                builds = config.get("Firebug" + version, "GECKO_VERSION").split(",")
                        except Exception as e:
                            print "[Error] Malformed config file: " + str(e)
                            continue
            		                    
                        print "[Info] Starting builds and FBTests for Firebug" + version
                        print self.testlist
                        # Run the build(s)
                        if not self.binary:
                            ret = self.prepare_builds(version, builds)
                        else:
                		    self.start_tests(version)
                		    
                        self.clean_temp_folder()
                		    
                        if ret != 0:
                            print ret
            except Exception as e:
        	    print "[Error] Could not run the FBTests"
        	    raise(e)
            		
            
            if not self.waitTime:
                break;
            
            # Wait for specified number of hours
            print "[Info] Sleeping for " + str(self.waitTime) + " hour" + ("s" if int(self.waitTime) > 1 else "")
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
                        
    parser.add_option("-v", "--version", dest="version",
                      help="The firebug version to run")
                        
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
    (opt, remainder) = parser.parse_args(argv)
    
    wrapper = FBWrapper(binary=opt.binary, profile=opt.profile, serverpath=opt.serverpath, version=opt.version, 
                                    couchURI=opt.couchURI, databasename=opt.databasename, testlist=opt.testlist, waitTime=opt.waitTime)
    wrapper.run()
   
if __name__ == '__main__':
     cli()
