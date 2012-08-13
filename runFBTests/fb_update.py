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
import fb_utils as utils
import mozlog
import os, sys
import optparse
import platform
import shutil
import socket
import subprocess
import time
import traceback
import urllib2
import urlparse

class FBUpdater:
    FIREBUG_REPO = "git://github.com/firebug/firebug.git"
    TESTLIST_LOCATION = "tests/content/firebug.html"
    CONFIG_LOCATION = "releases/firebug/test-bot.config"

    def __init__(self, **kwargs):
        # Set up the log file or use stdout if none specified
        self.log = mozlog.getLogger('FB_UPDATE', kwargs.get('log'))
        self.log.setLevel(mozlog.DEBUG if kwargs.get('debug') else mozlog.INFO)

        self.repo = kwargs.get('repo')
        self.serverpath = kwargs.get('serverpath')

    def _run_cmd(self, args, cwd=None, stdout=None):
        self.log.debug(" ".join(args))
        return subprocess.Popen(args, cwd=cwd, stdout=stdout).communicate()[0]

    def getRelativeURL(self, url):
        return urlparse.urlsplit(url).path.lstrip('/')

    def recursivecopy(self, src, dest):
        if not os.path.exists(dest):
            os.makedirs(dest)

        # Copy the files to the webserver document root (shutil.copytree won't work, settle for this)
        self.log.debug("Copying '%s' to '%s'" % (os.path.join(src, "*"), dest))
        if platform.system().lower() == "windows":
            subprocess.Popen("xcopy "+os.path.join(src, "*")+" "+dest+" /E", shell=True).wait()
        else:
            subprocess.Popen("cp -r "+os.path.join(src, '*')+" "+dest, shell=True).wait()

    def update(self):
        self.log.info("Updating server extensions and tests")

        # Get server's ip address
        dummy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        dummy.connect(('mozilla.org', 0))
        ip = dummy.getsockname()[0]

        # Grab the test_bot.config file
        utils.download("http://getfirebug.com/%s" % self.CONFIG_LOCATION, os.path.join(self.repo, "test-bot.config"))
        # Parse the config file
        test_bot = ConfigParser()
        test_bot.read(os.path.join(self.repo, "test-bot.config"))

        copyConfig = False
        tags = []
        # For each section in config file, download specified files and move to webserver
        for section in test_bot.sections():
            # Get information from config file
            if not (test_bot.has_option(section, "GIT_TAG") and test_bot.has_option(section, "GIT_BRANCH")):
                self.log.error("GIT_TAG and GIT_BRANCH must be specified for '%s'" % section)
                continue
            copyConfig = True

            GIT_BRANCH = test_bot.get(section, "GIT_BRANCH")
            GIT_TAG = test_bot.get(section, "GIT_TAG")

            #Ensure we have a git repo to work with
            fbugsrc = os.path.join(self.repo, "firebug")
            if not os.path.isdir(fbugsrc):
                self._run_cmd(["git","clone", self.FIREBUG_REPO, fbugsrc])

            # Create the branch in case it doesn't exist. If it does git will
            # spit out an error message which we can ignore
            self._run_cmd(["git","fetch","origin"], cwd=fbugsrc)
            self._run_cmd(["git","branch",GIT_BRANCH,"origin/%s" % GIT_BRANCH], cwd=fbugsrc)

            # Because we may have added new tags we need to pull before we find
            # our specific revision
            self._run_cmd(["git","checkout",GIT_BRANCH], cwd=fbugsrc)
            self._run_cmd(["git","reset","--hard","origin/%s" % GIT_BRANCH], cwd=fbugsrc)

            # Check out the tag for the git repo - this assumes we always work
            # off tags, branches or specific commit hashes.
            self._run_cmd(["git", "checkout", GIT_TAG], cwd=fbugsrc)

            # If using HEAD as a tag we need the actual changeset
            if GIT_TAG.upper() == "HEAD":
                GIT_TAG = self._run_cmd(["git", "rev-parse", GIT_TAG],
                            cwd=fbugsrc, stdout=subprocess.PIPE).strip()

            tags.append(GIT_TAG)

            # Localize testlist for the server
            testlist = "http://%s/%s/%s" % (ip, GIT_TAG, self.TESTLIST_LOCATION)
            test_bot.set(section, "TEST_LIST", testlist)

            if test_bot.has_option(section, "FIREBUG_XPI"):
                FIREBUG_XPI = test_bot.get(section, "FIREBUG_XPI")
                # Download the extensions
                firebug_path = self.getRelativeURL(FIREBUG_XPI)
                save_path = os.path.join(self.serverpath, firebug_path)
                self.log.debug("Downloading Firebug XPI '%s' to '%s'" % (FIREBUG_XPI, save_path)) 
                utils.download(FIREBUG_XPI, save_path)
            else:
                # build the extension from the source
                # requires java and ant on the webserver
                self.log.debug("Building Firebug extension from source")
                self._run_cmd(['ant'], cwd=os.path.join(fbugsrc, 'extension'))
                ext = os.path.join('extension', 'release')
                firebug_path = os.path.join(GIT_TAG, ext,
                                [f for f in os.listdir(os.path.join(fbugsrc, ext))
                                if f.startswith('firebug') if f.find('amo') == -1 if f.endswith('.xpi')][0])

            if test_bot.has_option(section, 'FBTEST_XPI'):
                FBTEST_XPI = test_bot.get(section, 'FBTEST_XPI')
                fbtest_path = self.getRelativeURL(FBTEST_XPI)
                save_path = os.path.join(self.serverpath, fbtest_path)
                self.log.debug("Downloading FBTest XPI '%s' to '%s'" % (FBTEST_XPI, save_path)) 
                utils.download(FBTEST_XPI, save_path)
            else:
                # build the extension from the source
                # requires java and ant on the webserver
                self.log.debug("Building FBTest extension from source")
                self._run_cmd(['ant'], cwd=os.path.join(fbugsrc, 'tests', 'FBTest'))
                ext = os.path.join('tests', 'FBTest', 'release')
                fbtest_path = os.path.join(GIT_TAG, ext,
                                [f for f in os.listdir(os.path.join(fbugsrc, ext))
                                if f.startswith('fbTest') if f.endswith('.xpi')][0])

            # Localize extensions for the server
            FIREBUG_XPI = "http://%s/%s" % (ip, firebug_path)
            test_bot.set(section, "FIREBUG_XPI", FIREBUG_XPI)

            FBTEST_XPI = "http://%s/%s" % (ip, fbtest_path)
            test_bot.set(section, "FBTEST_XPI", FBTEST_XPI)

            # Copy this to the serverpath
            self.recursivecopy(fbugsrc, os.path.join(self.serverpath, GIT_TAG))

        if copyConfig:
            # Write the complete config file
            saveloc = os.path.join(self.serverpath, os.path.dirname(self.CONFIG_LOCATION))
            if not os.path.exists(saveloc):
                os.makedirs(saveloc)
            with open(os.path.join(self.serverpath, self.CONFIG_LOCATION), 'wb') as configfile:
                test_bot.write(configfile)

        # Remove old revisions to save space
        tags.extend(["releases", "tests"])
        for name in os.listdir(self.serverpath):
            path = os.path.join(self.serverpath, name)
            if name not in tags and os.path.isdir(path):
                # only remove if it is more than a day old
                # this is so we don't delete files that are currently being used in the middle of a test run
                mtime = os.path.getmtime(path)
                if time.time() - mtime > 24 * 60 * 60: # number of seconds in a day
                    self.log.debug("Deleting unused changeset: %s" % path)
                    shutil.rmtree(path)

def main(argv=sys.argv[1:]):
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
            log.info("Sleeping for %s hour%s" % (opt.waitTime, "s" if int(opt.waitTime) > 1 else ""))
            time.sleep(int(opt.waitTime) * 3600)
        else:
            break;
    mozlog.shutdown()


if __name__ == '__main__':
    sys.exit(main())
