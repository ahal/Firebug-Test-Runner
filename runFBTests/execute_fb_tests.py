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
import os, sys
import optparse
import shutil
import subprocess
import tempfile
import platform

if platform.system().lower() == "windows":
    import zipfile
else:
    import tarfile

# Global changeset variable
changeset = {}

def clean_temp_folder(tempdir, build=False):
    """
    Clean the temporary directory
    """
    try:
        if build:
            if platform.system().lower() != "darwin":
                bundle = os.path.join(tempdir, "mozilla-" + build + (".zip" if platform.system().lower()=="windows" else ".tar.bz2"))
                if os.path.isfile(bundle):
                    os.remove(bundle)
            if os.path.isdir(os.path.join(tempdir, "mozilla-" + build)):
                shutil.rmtree(os.path.join(tempdir, "mozilla-" + build))
        for filename in os.listdir(tempdir):
            if os.path.isdir(os.path.join(tempdir, filename)) and filename[0:3] == "tmp":            
                shutil.rmtree(os.path.join(tempdir, filename))
    except Exception as e:
        print "[Warn] Could not delete temporary files in '" + basedir + "': " + str(ret)

def build_needed(build, buildpath):
    """
    Return True if the tests have never been run against the current changeset of 'build'
    Return False otherwise
    """
    # Find new changeset
    new_changeset = fb_run.get_changeset(buildpath)
    global changeset
    if not build in changeset:
        changeset[build] = -1
    if changeset[build] != new_changeset:
        changeset[build] = new_changeset
        return True
    return False

def prepare_builds(argv, version, basedir, builds):
    """
    Downloads the builds and starts the tests
    """
    # Lookup table mapping Firefox versions to Gecko versions (as specified in Firebug's test-bot.config)
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : 'central', '4.0' : 'central' }

    # For each version of Firefox, see if it needs to be rebuilt and call fb_run to run the tests
    for build in builds:
        build = lookup[build]
        print "[Info] Running Firebug" + version + " tests against Mozilla " + build

        # Scrape for the latest tinderbox build and extract it to the basedir
        try:
            # Location to save the tinderbox build
            buildPath = os.path.join(basedir, "mozilla-" + build);
            
            # Get the url to the latest tinderbox build
            proc = subprocess.Popen("get-latest-tinderbox --product=mozilla-" + build, shell=True, stdout=subprocess.PIPE)
            tinderbox_url = proc.communicate()[0]
            
            # Download and extract the tinderbox build
            if platform.system().lower() == "darwin":
                fb_run.retrieve_url(tinderbox_url, os.path.join(buildPath, "firefox.dmg"))
                proc = subprocess.Popen("hdiutil mount " + os.path.join(buildPath,  "firefox.dmg"), shell=True, stdout=subprocess.PIPE)
                for data in proc.communicate()[0].split():
                    if data.find("/Volumes/") != -1:
                        appDir = data
                for files in os.listdir(appDir):
                    print files
                    if files[-4:] == ".app":
                        appName = files
                        break
                print "App dir: " + appDir + " Name: " + appName
                subprocess.call("cp -r " + os.path.join(appDir, appName) + " " + buildPath, shell=True)
                subprocess.call("hdiutil unmount " + appDir, shell=True)
                buildPath = os.path.join(buildPath, appName)
            	print "Buildpath: " + buildPath
                print os.path.isdir(buildPath)
            else:
                if platform.system().lower() == "windows":
                    fb_run.retrieve_url(tinderbox_url, buildPath + ".zip")
                    bundle = zipfile.ZipFile(buildPath + ".zip")
                else:
                    fb_run.retrieve_url(tinderbox_url, buildPath + ".tar.bz2")
                    bundle = tarfile.open(buildPath + ".tar.bz2")
                bundle.extractall(buildPath)
                bundle.close()
                buildPath = os.path.join(buildPath, "firefox")
        except Exception as e:
            print "[Error] Could not grab the latest tinderbox build: " + str(e)
            continue
        
        # If the newest tinderbox changeset is different from the previously run changeset
        if build_needed(build, buildPath):
            # Set the build path (in argv)
            argv.append("-b")
            if platform.system().lower() == "darwin":
                argv.append(buildPath)
            else:
                argv.append(os.path.join(buildPath, "firefox" + (".exe" if platform.system().lower()=="windows" else "")))
            fb_run.main(argv)
        else:
            print "[Info] Tests already run with this changeset"
                
        # Remove build directories and temp files
        clean_temp_folder(basedir, build)
        
    return 0

def main(argv):
    """
    Module initialization and loop
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
                        
    parser.add_option("-c", "--couch", dest="couchserveruri",
                      help="URI to couchdb server for log information")
                        
    parser.add_option("-d", "--database", dest="databasename",
                      help="Database name to keep log information")
                        
    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Url to the testlist to use")
                      
    parser.add_option("--interval", dest="waitTime",
                      help="Number of hours to wait between test runs. If unspecified tests are only run once")
    (opt, remainder) = parser.parse_args(argv)

    # Ensure serverpath has correct format
    opt.serverpath = ("" if opt.serverpath[0:7] == "http://" else "http://") + opt.serverpath
    opt.serverpath += ("" if opt.serverpath[-1] == "/" else "/")
    
    # Temporary directory to store tinderbox builds and temporary profiles
    tempdir = tempfile.gettempdir();
    print "Temp folder: " + tempdir
        
    # Remove waitTime as fb_run doesn't use it
    if opt.waitTime:
        index = argv.index("--interval")
        argv.pop(index + 1)
        argv.pop(index)

    while 1:
    
    	# Download test-bot.config to see which versions of Firefox to run the FBTests against
    	if fb_run.retrieve_url(opt.serverpath + "releases/firebug/test-bot.config", "test-bot.config") != 0:
    	    print "[Error] Could not download 'test-bot.config' from '" + opt.serverpath + "'"
        
        config = ConfigParser()
        config.read("test-bot.config")
        
        for section in config.sections():
            version = section[-3:]
            if not opt.version:
                if argv.count("-v") == 0:
                    argv.append("-v")
                    argv.append(version)
                else:
                    index = argv.index("-v")
                    argv[index + 1] = version
            
            if not opt.version or version == opt.version:
                if not opt.testlist:
                    testlist = config.get("Firebug" + version, "TEST_LIST")
                    testlist = testlist.replace("http://getfirebug.com/", opt.serverpath)
                    argv.append("-t")
                    argv.append(testlist)
                if not opt.binary:
                    builds = config.get("Firebug" + version, "FIREFOX_VERSION").split(",")
    		                    
                print "[Info] Starting builds and FBTests for Firebug" + version
        		
                # Run the build(s)
                if not opt.binary:
                    ret = prepare_builds(argv, version, tempdir, builds)
                else:
        		    ret = fb_run.main(argv)
        		    
                clean_temp_folder(tempdir)
        		    
                if ret != 0:
                    print ret
        		
        
        if not opt.waitTime:
            break;
        
        # Wait for specified number of hours
        print "[Info] Sleeping for " + str(opt.waitTime) + " hour" + ("s" if int(opt.waitTime) > 1 else "")
        sleep(int(opt.waitTime) * 3600)
        
        if os.path.isfile("test-bot.config"):
            os.remove("test-bot.config")
        
        
        
if __name__ == '__main__':
    main(sys.argv[1:])
