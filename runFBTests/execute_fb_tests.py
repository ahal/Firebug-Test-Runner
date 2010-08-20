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
import get_latest
import os, sys
import optparse
import shutil
import tempfile
import platform

if platform.system().lower() == "windows":
    import zipfile
else:
    import tarfile

# Global changeset variable
changeset = {}

def clean_temp_folder(tempdir, build):
    """
    Clean the temporary directory
    """
    try:
        bundle = os.path.join(tempdir, "mozilla-" + build + (".zip" if platform.system().lower()=="windows" else ".tar.bz2"))
        if os.path.isfile(bundle):
            os.remove(bundle)
        if os.path.isdir(os.path.join(tempdir, "mozilla-" + build)):
            shutil.rmtree(os.path.join(tempdir, "mozilla-" + build))
        for filename in os.listdir(tempdir):
            if os.path.isdir(os.path.join(tempdir, filename)) and filename[0:3] == "tmp":            
                shutil.rmtree(os.path.join(tempdir,filename))
    except Exception as e:
        return e
    return 0

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

def run_builds(argv, opt, basedir):
    """
    Runs the firefox tests
    """
    # Lookup table mapping Firefox versions to Gecko versions
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : 'central', '4.0' : 'central' }
    # Download test-bot.config to see which versions of Firefox to run the FBTests against
    opt.serverpath = ("" if opt.serverpath[0:7] == "http://" else "http://") + opt.serverpath
    opt.serverpath += ("" if opt.serverpath[-1] == "/" else "/")
    if fb_run.retrieve_url(opt.serverpath + "releases/firebug/test-bot.config", "test-bot.config") != 0:
        return "[Error] Could not download 'test-bot.config' from '" + opt.serverpath + "'"
    
    config = ConfigParser()
    config.read("test-bot.config")
    
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    # Grab the testlist specified in test-bot.config
    try:
        testlist = config.get("Firebug" + opt.version, "TEST_LIST")
        testlist = testlist.replace("http://getfirebug.com/", opt.serverpath)
    except:
        testlist = None
        pass
    os.remove("test-bot.config")
    ret = 0
    # For each version of Firefox, see if it needs to be rebuilt and call fb_run to run the tests
    for build in builds:
        build = lookup[build]
        print "[Info] Running Firebug" + opt.version + " tests against Mozilla " + build

        try:
            # Scrape for the latest tinderbox build and extract it to the basedir
            saveLocation = os.path.join(basedir, "mozilla-" + build);
            if platform.system().lower() == "windows":
                fb_run.retrieve_url(get_latest.main(["--product=mozilla-" + build]), saveLocation + ".zip")
                bundle = zipfile.ZipFile(saveLocation + ".zip")
            else:
                fb_run.retrieve_url(get_latest.main(["--product=mozilla-" + build]), saveLocation + ".tar.bz2")
                bundle = tarfile.open(saveLocation + ".tar.bz2")
            bundle.extractall(saveLocation)
            bundle.close()
        except IOError as e:
            print "[Error] Could not grab the latest tinderbox build: " + str(e)
            continue
        
        if build_needed(build, os.path.join(saveLocation, "firefox/")):
            # Run fb_run with synthesized argv
            if opt.testlist == None and testlist != None:
                argv[-3] = testlist
            argv[-1] = os.path.join(saveLocation, "firefox", "firefox" + (".exe" if platform.system().lower()=="windows" else ""))
            ret = fb_run.main(argv)
            if ret != 0:
                print ret
                
        # Remove build directories and temp files
        ret = clean_temp_folder(basedir, build)
        if ret != 0:
            print "[Warn] Could not delete temporary files in '" + basedir + "': " + str(ret)
        
    return 0

def main(argv):
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-p", "--profile", dest="profile",
                      help="The profile to use when running Firefox")
                        
    parser.add_option("-s", "--serverpath", dest="serverpath",
                      default="http://getfirebug.com",
                      help="The http server containing the firebug tests")
                        
    parser.add_option("-v", "--version", dest="version",
                      default="1.6",
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
    
    # Synthesize arguments to be passed to fb_run
    if opt.testlist == None:
        argv.append("-t")
        argv.append("testlist")     # Placeholder    
    argv.append("-b")
    argv.append("buildpath")        # Placeholder
    if opt.waitTime:
        index = argv.index("--interval")
        argv.pop(index + 1)
        argv.pop(index)
    # Temporary directory to store tinderbox builds and temporary profiles
    tempdir = tempfile.gettempdir();

    ret = True
    while ret != "quit":
        print "[Info] Starting builds and FBTests for Firebug" + opt.version
        
        # Run the builds and catch any exceptions that may have been missed
        ret = run_builds(argv, opt, tempdir)
        if ret != 0:
            print ret
        
        if not opt.waitTime:
            break;
            
        # Wait for specified number of hours
        print "[Info] Sleeping for " + str(opt.waitTime) + " hour" + ("s" if opt.waitTime > 1 else "")
        sleep(opt.waitTime * 3600)
        
    
if __name__ == '__main__':
    main(sys.argv[1:])