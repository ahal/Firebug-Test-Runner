# coding=UTF-8
## This script will grab all of the latest firebug releases, as well as 
## the fbtests and testlists and store them on the specified webserver
from ConfigParser import ConfigParser
import os, sys, getopt

# Initialization
config = ConfigParser()
config.read("./fb-test-runner.config")
# Retrieve server path from config file or command line
serverpath = config.get("update", "serverpath")
# Parse command line
try:
    opts, args = getopt.getopt(sys.argv[1:], "s:")
except getopt.GetoptError, err:
    print str(err)
    sys.exit(2)
for o, a in opts:
    if o == "-s":
        serverpath = a
    else:
        assert False, "Unhandled command line option"

# Grab the test_bot.config file
os.system("wget -N http://getfirebug.com/releases/firebug/test-bot.config")
test_bot = ConfigParser()
test_bot.read(os.getcwd() + "/test-bot.config")
# For each section in the config file, download the specified files and move them to the webserver
for section in test_bot.sections():
    if not os.path.isdir(os.path.curdir + section + "/.svn"):
        os.system("svn co http://fbug.googlecode.com/svn/tests/" + " " + os.getcwd() + "/" + section.lower() + "/tests -r " + test_bot.get(section, "SVN_REVISION"))
    else:
        os.system(section.lower() + "/svn update -r " + test_bot.get(section, "SVN_REVISION"))
    os.system("wget --output-document=./" + section.lower() + "/firebug.xpi" + " " + test_bot.get(section, "FIREBUG_XPI"))
    os.system("wget --output-document=./" + section.lower() + "/fbtest.xpi" + " " + test_bot.get(section, "FBTEST_XPI"))
    os.system("cp -r ./" + section.lower() + " " + serverpath)
    