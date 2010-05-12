# coding=UTF-8
## This script will grab all of the latest firebug releases, as well as 
## the fbtests and testlists and store them on the specified webserver
from ConfigParser import ConfigParser
import os, sys, getopt

# Initialization
config = ConfigParser()
config.read(os.getcwd() + "/fb-test-runner.config")
# Parse command lines
try:
    opts, args = getopt.getopt(sys.argv[1:], "s:")
except getopt.GetoptError, err:
    print str(err) # will print something like "option -a not recognized"
    sys.exit(2)
# Retrieve server path from config file or command line
serverpath = config.get("update", "serverpath")
for o, a in opts:
    if o == "-s":
        serverpath = a
    else:
        assert False, "unhandled option"

# Grab the test_bot.config file
os.system("wget -N http://getfirebug.com/releases/firebug/test-bot.config")
test_bot = ConfigParser()
test_bot.read(os.getcwd() + "/test-bot.config")
# For each section in the config file, download the specified files and move them to the webserver
for section in test_bot.sections():
    os.system("wget -N --directory-prefix=./" + section.lower() + " " + test_bot.get(section, "FIREBUG_XPI"))
    os.system("wget -N --directory-prefix=./" + section.lower() + " " + test_bot.get(section, "FBTEST_XPI"))
    if not os.path.isdir(os.path.curdir + section + "/.svn"):
        os.system("svn co " + " http://fbug.googlecode.com/svn/tests/" + " " + os.getcwd() + "/" + section.lower() + "/tests -r " + test_bot.get(section, "SVN_REVISION"))
    else:
        os.system(section.lower() + "/svn update -r " + test_bot.get(section, "SVN_REVISION"))
    os.system("cp -r ./" + section.lower() + " " + serverpath)
    