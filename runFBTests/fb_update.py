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
import os, sys
import shutil
import optparse
import urllib2
    
def retrieve_url(url, filename):
    """
    Save the file located at 'url' into 'filename'
    """
    try:
        ret = urllib2.urlopen(url)
    except:
        return -1
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()
    return 0
    
def update(opt):
    # Grab the test_bot.config file
    configDir = "releases/firebug/test-bot.config"
    retrieve_url("http://getfirebug.com/" + configDir, os.path.join(opt.repo, configDir))
    
    # Parse the config file
    test_bot = ConfigParser()
    test_bot.read("files/" + configDir)
    
    # For each section in config file, download specified files and move to webserver
    for section in test_bot.sections():
        # Grab file locations
        SVN_REVISION = test_bot.get(section, "SVN_REVISION")
        FIREBUG_XPI = test_bot.get(section, "FIREBUG_XPI")
        FBTEST_XPI = test_bot.get(section, "FBTEST_XPI")
        
        # Update or create the svn test repository
        if not os.path.isdir(os.path.join("files", ".svn")):
            os.system("svn co http://fbug.googlecode.com/svn/tests/ " + os.path.join(opt.repo, "tests") + " -r " + SVN_REVISION)
        else:
            os.system(os.path.join(opt.repo, "svn") + " update -r " + SVN_REVISION)
        
        # Download the extensions
        retrieve_url(FIREBUG_XPI, os.path.join(opt.repo, FIREBUG_XPI[FIREBUG_XPI.find("getfirebug.com/")+15:]))
        retrieve_url(FBTEST_XPI, os.path.join(opt.repo, FBTEST_XPI[FBTEST_XPI.find("getfirebug.com/")+15:]))
        
        # Copy the files to the webserver
        os.system("cp -r " + os.path.join(opt.repo, "*") + " " + opt.serverpath)

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
                      default=12,
                      help="The number of hours to wait between checking for updates")
    (opt, remainder) = parser.parse_args(argv)
    
    if not os.path.exists(opt.repo):
        os.mkdir(opt.repo)

    while (1):
        print "[INFO] Updating server extensions and tests"
        update(opt)
        print "[INFO] Sleeping for " + opt.waitTime + " hour" + ("s" if opt.waitTime > 1 else "")
        sleep(opt.waitTime * 3600)


if __name__ == '__main__':
    main(sys.argv[1:])