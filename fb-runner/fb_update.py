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
# the fbtests and testlists and store them on the specified webserver
from ConfigParser import ConfigParser
from time import sleep
import os, sys, optparse

def create_custom_testlist(name, exceptions, version):
    file = open("firebug" + version + "/tests/content/testlists/firebug" + version + ".html", "r")
    text = file.readlines()
    file.close()
    for exception in exceptions:
        for line in range(len(text)):
            if text[line].find(exception) != -1:  
                text[line] = ""
                break
    file = open("firebug" + version + "/tests/content/testlists/" + name, "w")
    file.writelines(text)
    file.close()
    
def update(opt):
    # Grab the test_bot.config file
    os.system("wget -N http://getfirebug.com/releases/firebug/test-bot.config")
    test_bot = ConfigParser()
    test_bot.read("test-bot.config")
    # For each section in the config file, download the specified files and move them to the webserver
    for section in test_bot.sections():
        if not os.path.isdir(os.path.join(section.lower(), ".svn")):
            os.system("svn co http://fbug.googlecode.com/svn/tests/" + " " + os.path.join(section.lower(), "tests") + " -r " + test_bot.get(section, "SVN_REVISION"))
        else:
            os.system(os.path.join(section.lower(), "svn") + " update -r " + test_bot.get(section, "SVN_REVISION"))
            
        # Create custom testlist
        if opt.testlistname != None:            
            create_custom_testlist(opt.testlistname, opt.exceptlist.split(","), section[-3:])
        os.system("wget --output-document=" + os.path.join(section.lower(), "firebug.xpi") + " " + test_bot.get(section, "FIREBUG_XPI"))
        os.system("wget --output-document=" + os.path.join(section.lower(), "fbtest.xpi") + " " + test_bot.get(section, "FBTEST_XPI"))
        os.system("cp -r " + section.lower() + " " + opt.serverpath)


def main(argv):
    # Initialization
    config = ConfigParser()
    try:
        config.read("fb-test-runner.config")
    except ConfigParser.NoSectionError:
        print "[Warn] Could not find 'fb-test-runner.config' in local directory"
        file = open("fb-test-runner.config", "w")
        file.close()
        config.read("fb-test-runner.config")

    # Parse command line
    parser = optparse.OptionParser("%prog [options]")
    parser.add_option("-s", "--serverpath", dest="serverpath",
                      default=config.get("update", "serverpath"),
                      help="Path to the Apache2 document root Firebug directory")
                        
    parser.add_option("-t", "--testlistname", dest="testlistname",
                      help="When specified, creates a custom testlist excluding the tests specified in the -e argument")
                        
    parser.add_option("-e", "--except", dest="exceptlist",
                      help="A comma separated list of tests to exclude from the custom testlist.  The -t argument must specify a name")
    (opt, remainder) = parser.parse_args(argv)

    while (1):
        print "[INFO] Updating server extensions and tests"
        update(opt)
        print "[INFO] Sleeping for 12 hours"
        sleep(43200)


if __name__ == '__main__':
    main(sys.argv[1:])