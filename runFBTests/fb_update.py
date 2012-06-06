# coding=UTF-8
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

# This script will grab all of the latest firebug releases, as well as
# the fbtests and testlists and store them on the local webserver
from ConfigParser import ConfigParser
from time import sleep
import fb_utils as utils
import fileinput
import os, sys
import subprocess
import shutil
import optparse
import urllib2
import urlparse
import socket
import platform
import mozlog
import traceback

class FBUpdater:
    FIREBUG_REPO = "https://github.com/firebug/firebug.git"
    TESTLIST_LOCATION = "tests/content/firebug.html"
    CONFIG_LOCATION = "releases/firebug/test-bot.config"

    def __init__(self, **kwargs):
        # Set up the log file or use stdout if none specified
        self.log = mozlog.getLogger('FB_UPDATE', kwargs.get('log'))
        self.log.setLevel(mozlog.DEBUG if kwargs.get('debug') else mozlog.INFO)

        self.repo = kwargs.get('repo')
        self.serverpath = kwargs.get('serverpath')

    def getRelativeURL(self, url):
        return urlparse.urlsplit(url).path.lstrip('/')

    def recursivecopy(self, src, dest):
        if not os.path.exists(dest):
            os.makedirs(dest)

        # Copy the files to the webserver document root (shutil.copytree won't work, settle for this)
        if platform.system().lower() == "windows":
            subprocess.Popen("xcopy " + os.path.join(src, "*") + " " + dest + "/E",
                    shell=True).wait()
            self.log.debug("xcopy " + os.path.join(src, "*") + " " + dest + "/E")
        else:
            subprocess.Popen("cp -r " + os.path.join(src, "*") + " " + dest,
                    shell=True).wait()
            self.log.debug("cp -r " + os.path.join(src, "*") + " " + dest)

    def update(self):
        self.log.info("Updating server extensions and tests")

        # Get server's ip address
        dummy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dummy.connect(('mozilla.org', 0))
        ip = dummy.getsockname()[0]

        # Grab the test_bot.config file
        utils.download("http://getfirebug.com/" + self.CONFIG_LOCATION, os.path.join(self.repo, "test-bot.config"))
        # Parse the config file
        test_bot = ConfigParser()
        test_bot.read(os.path.join(self.repo, "test-bot.config"))

        copyConfig = False
        # For each section in config file, download specified files and move to webserver
        for section in test_bot.sections():
            # Get information from config file
            if not (test_bot.has_option(section, "GIT_TAG") and test_bot.has_option(section, "GIT_BRANCH")):
                self.log.error("GIT_TAG and GIT_BRANCH must be specified for '" + section + "'")
                continue
            copyConfig = True
            
            GIT_BRANCH = test_bot.get(section, "GIT_BRANCH")
            GIT_TAG = test_bot.get(section, "GIT_TAG")

            #Ensure we have a git repo to work with
            fbugsrc = os.path.join(self.repo, "firebug")
            if not os.path.isdir(fbugsrc):
                self.log.debug("git clone " + self.FIREBUG_REPO + " " + fbugsrc)
                subprocess.Popen(["git","clone", self.FIREBUG_REPO, fbugsrc]).communicate()

            # Create the branch in case it doesn't exist. If it does git will
            # spit out an error message which we can ignore
            self.log.debug("git branch " + GIT_BRANCH + " origin/" + GIT_BRANCH)
            subprocess.Popen(["git","branch",GIT_BRANCH,"origin/"+GIT_BRANCH],
                    cwd=fbugsrc).communicate()

            # Because we may have added new tags we need to pull before we find
            # our specific revision
            self.log.debug("git checkout " + GIT_BRANCH)
            subprocess.Popen(["git","checkout",GIT_BRANCH], cwd=fbugsrc).communicate()
            self.log.debug("git pull origin " + GIT_BRANCH)
            subprocess.Popen(["git", "pull" , "origin", GIT_BRANCH],
                    cwd=fbugsrc).communicate()

            # Check out the tag for the git repo - this assumes we always work
            # off tags, branches or specific commit hashes.
            self.log.debug("git checkout " + GIT_TAG)
            subprocess.Popen(["git", "checkout", GIT_TAG], cwd=fbugsrc).communicate()

            # If using HEAD as a tag we need the actual changeset
            if GIT_TAG.upper() == "HEAD":
                GIT_TAG = subprocess.Popen(["git", "rev-parse", GIT_TAG],
                            cwd=fbugsrc, stdout=subprocess.PIPE).communicate()[0].strip()

            # Copy this to the serverpath
            self.recursivecopy(fbugsrc, os.path.join(self.serverpath, GIT_TAG))
        
            # Localize testlist for the server
            testlist = "http://" + ip + "/" + GIT_TAG + "/" + self.TESTLIST_LOCATION
            test_bot.set(section, "TEST_LIST", testlist)

            FIREBUG_XPI = test_bot.get(section, "FIREBUG_XPI")
            FBTEST_XPI = test_bot.get(section, "FBTEST_XPI")
        
            # Download the extensions
            firebugPath = self.getRelativeURL(FIREBUG_XPI)
            savePath = os.path.join(self.serverpath, firebugPath)
            self.log.debug("Downloading Firebug XPI '" + FIREBUG_XPI + "' to '" + savePath + "'")
            utils.download(FIREBUG_XPI, savePath)

            fbtestPath = self.getRelativeURL(FBTEST_XPI)
            savePath = os.path.join(self.serverpath, fbtestPath)
            self.log.debug("Downloading FBTest XPI '" + FBTEST_XPI + "' to '" + savePath + "'")
            utils.download(FBTEST_XPI, savePath)
        
            # Localize extensions for the server
            FIREBUG_XPI = "http://" + ip + "/" + firebugPath
            test_bot.set(section, "FIREBUG_XPI", FIREBUG_XPI)

            FBTEST_XPI = "http://" + ip + "/" + fbtestPath
            test_bot.set(section, "FBTEST_XPI", FBTEST_XPI)

        if copyConfig:
            # Write the complete config file
            with open(os.path.join(self.serverpath, self.CONFIG_LOCATION), 'wb') as configfile:
                test_bot.write(configfile)

def main(argv):
    # Parse command line
    parser = optparse.OptionParser("%prog [options]")
    parser.add_option("-d", "--document-root", dest="serverpath",
                      default="/var/www",
                      help="Path to the Apache2 document root Firebug directory")

    parser.add_option("--repo", dest="repo",
                      default=os.path.join(os.getcwd(), "files"),
                      help="Location to create or update the local FBTest repository")

    parser.add_option("-i", "--interval", dest="waitTime",
                      help="The number of hours to wait between checking for updates")

    parser.add_option("--debug", dest="debug",
                      action="store_true",
                      help="Enables debug logging")

    (opt, remainder) = parser.parse_args(argv)
    
    if not os.path.exists(opt.repo):
        os.mkdir(opt.repo)


    updater = FBUpdater(repo=opt.repo, serverpath=opt.serverpath, debug=opt.debug)
    log = mozlog.getLogger("FB_UPDATE")

    while (1):
        try:
            updater.update()
        except Exception as e:
            log.error(traceback.format_exc())
        if opt.waitTime != None:
            log.info("Sleeping for " + str(opt.waitTime) + " hour" + ("s" if int(opt.waitTime) > 1 else ""))
            sleep(int(opt.waitTime) * 3600)
        else:
            break;
    mozlog.shutdown()


if __name__ == '__main__':
    main(sys.argv[1:])
