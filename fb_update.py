# coding=UTF-8
## This script will grab all of the latest firebug releases, as well as 
## the fbtests and testlists and store them on the specified webserver
from ConfigParser import ConfigParser
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
    

def main(argv):
    # Initialization
    config = ConfigParser()
    config.read("./fb-test-runner.config")

    # Parse command line
    parser = optparse.OptionParser("%prog [options]")
    parser.add_option("-s", "--serverpath", dest="serverpath", default=config.get("update", "serverpath"), help="Path to the Apache2 document root Firebug directory")
    parser.add_option("-t", "--testlistname", dest="testlistname", help="When specified, creates a custom testlist excluding the tests specified in the -e argument")
    parser.add_option("-e", "--except", dest="exceptlist", help="A comma separated list of tests to exclude from the custom testlist.  The -t argument must specify a name")
    (opt, remainder) = parser.parse_args(argv)

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
            
        # Create custom testlist
        if not opt.testlistname == None:            
            create_custom_testlist(opt.testlistname, opt.exceptlist.split(","), section[-3:])
        os.system("wget --output-document=./" + section.lower() + "/firebug.xpi" + " " + test_bot.get(section, "FIREBUG_XPI"))
        os.system("wget --output-document=./" + section.lower() + "/fbtest.xpi" + " " + test_bot.get(section, "FBTEST_XPI"))
        os.system("cp -r ./" + section.lower() + " " + opt.serverpath)


if __name__ == '__main__':
    main(sys.argv[1:])