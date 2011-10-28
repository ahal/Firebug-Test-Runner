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

def getRelativeURL(url):
    return urlparse.urlsplit(url).path.lstrip('/')

def update(opt):
    # Get server's ip address
    dummy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dummy.connect(('google.com', 0))
    ip = dummy.getsockname()[0]

    # Grab the test_bot.config file
    configDir = "releases/firebug/test-bot.config"
    utils.download("http://getfirebug.com/" + configDir, os.path.join(opt.repo, configDir))

    # Parse the config file
    test_bot = ConfigParser()
    test_bot.read(os.path.join(opt.repo, configDir))

    # For each section in config file, download specified files and move to webserver
    for section in test_bot.sections():
        # Grab config information
        SVN_REVISION = test_bot.get(section, "SVN_REVISION")
        FIREBUG_XPI = test_bot.get(section, "FIREBUG_XPI")
        FBTEST_XPI = test_bot.get(section, "FBTEST_XPI")

        # Update or create the svn test repository
        if not os.path.isdir(os.path.join(opt.repo, ".svn")):
            os.system("svn co http://fbug.googlecode.com/svn/tests/ " + os.path.join(opt.repo, SVN_REVISION, "tests") + " -r " + SVN_REVISION)
        else:
            os.system(os.path.join(opt.repo, "svn") + " update -r " + SVN_REVISION)

        # Download the extensions
        print FIREBUG_XPI
        relPath = getRelativeURL(FIREBUG_XPI)
        savePath = os.path.join(opt.repo, relPath)
        utils.download(FIREBUG_XPI, savePath)

        print FBTEST_XPI
        relPath = getRelativeURL(FBTEST_XPI)
        savePath = os.path.join(opt.repo, relPath)
        utils.download(FBTEST_XPI, savePath)

        # Localize extensions for the server
        relPath = getRelativeURL(FIREBUG_XPI)
        FIREBUG_XPI = "http://" + ip + "/" + relPath
        test_bot.set(section, "FIREBUG_XPI", FIREBUG_XPI)

        relPath = getRelativeURL(FBTEST_XPI)
        FBTEST_XPI = "http://" + ip + "/" + relPath
        test_bot.set(section, "FBTEST_XPI", FBTEST_XPI)

        # Localize testlist for the server
        testlist = test_bot.get(section, "TEST_LIST")
        relPath = getRelativeURL(testlist)
        testlist = "http://" + ip + "/" + SVN_REVISION + "/" + relPath
        test_bot.set(section, "TEST_LIST", testlist)

    with open(os.path.join(opt.repo, configDir), 'wb') as configfile:
        test_bot.write(configfile)

    # Copy the files to the webserver document root (shutil.copytree won't work, settle for this)
    if platform.system().lower() == "windows":
        os.system("xcopy " + os.path.join(opt.repo, "*") + " " + opt.serverpath + "/E")
        print "xcopy " + os.path.join(opt.repo, "*") + " " + opt.serverpath + "/E"
    else:
        os.system("cp -r " + os.path.join(opt.repo, "*") + " " + opt.serverpath)
        print "cp -r " + os.path.join(opt.repo, "*") + " " + opt.serverpath

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

    (opt, remainder) = parser.parse_args(argv)

    if not os.path.exists(opt.repo):
        os.mkdir(opt.repo)

    while (1):
        print "[INFO] Updating server extensions and tests"
        try:
            update(opt)
        except Exception as e:
            print "[Error] Could not update the server files: " + str(e)
        if opt.waitTime != None:
            print "[INFO] Sleeping for " + str(opt.waitTime) + " hour" + ("s" if int(opt.waitTime) > 1 else "")
            sleep(int(opt.waitTime) * 3600)
        else:
            break;


if __name__ == '__main__':
    main(sys.argv[1:])
