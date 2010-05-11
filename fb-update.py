# coding=UTF-8
## This script will grab all of the latest firebug releases (one for each version), as well as 
## the fbtests and testlists and store them in the current directory
from ConfigParser import ConfigParser
import urllib, sgmllib, sys, os, pysvn, zipfile, glob, getopt

class LinkParser(sgmllib.SGMLParser):
    "Class for parsing HTML hyperlinks"
    def __init__(self, verbose=0):
        "Initialize parse object"
        sgmllib.SGMLParser.__init__(self, verbose)
        self.links = []
    def parse(self, s):
        "Parse string s"
        self.feed(s)
        self.close()
    def start_a(self, attributes):
        "Process a hyperlink and its attributes"
        for name, value in attributes:
            if name == "href":
                self.links.append(value)
    def get_links(self):
        "Return the hyperlinks"
        return self.links

# Helper to return a list of links from a website
def get_links(url):
    # HTTP Request
    f = urllib.urlopen(url)
    s = f.read()
    f.close()
    # Parse the response
    parser = LinkParser()
    parser.parse(s)
    return parser.get_links()
    
# Return 1 is b is greater than a, 0 otherwise
def compare_firebug(a, b):
    if a == "" and b != "": return 1
    elif a != "" and b == "": return 0
    a, b = a.split("."), b.split(".")
    try:
        if int(a[0]) < int(b[0]) or int(a[1].replace("X", "")) < int(b[1].replace("X", "")) or int(a[2][0]) < int(b[2][0]) or a[2][1] < b[2][1] or int(a[2][2:]) < int(b[2][2:]):
            return 1
    except IndexError:
        if len(a[2]) < len(b[2]):
            return 1
    return 0

def extract_xpi(url):
    links = get_links(url)
    # Find maximum version number
    max = ""
    for link in links:
        try:
            if link[0:7] == "firebug" and compare_firebug(max[8:-4], link[8:-4]) == 1:
                max = link
        except IndexError:
            pass
    # Grab the most recent .xpi file
    os.system("wget -N " + url + max)

def make_archive(dir, zipper, base=""):
    """
        Zips the contents of the directory specified by 'dir' into the zipper
        specified by 'zipper'.  Base is used for recursion and should not be used when calling the method
    """
    try:
        for file in glob.glob(dir + "/*"):
            if os.path.isdir(file):
                make_archive(file, zipper, base + os.path.basename(file) + "/")
            else:
                zipper.write(file, base + os.path.basename(file), zipfile.ZIP_DEFLATED)
        return 1
    except: return 0


# Initialization
config = ConfigParser()
config.read(os.getcwd() + "/fbtest.conf")
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


# Get list of currently available versions and download them
##links = get_links("http://getfirebug.com/releases/firebug/")
##for link in links:
##    try:
##        if int(link[0]):
##            extract_xpi("http://getfirebug.com/releases/firebug/" + link)
##    except ValueError:
##        pass
##        
##        
client = pysvn.Client()
### Get the current test extensions from svn
##if not os.path.isdir(os.path.curdir + "/fbtest/.svn"):
##    client.checkout("http://fbug.googlecode.com/svn/fbtest/", os.getcwd() + "/fbtest")
##else:
##    client.update(os.path.curdir + "/fbtest")
##for dir in os.listdir(os.path.curdir + "/fbtest/branches"):
##    if os.path.isdir(os.path.curdir + "/fbtest/branches/" + dir) and dir[:6] == "fbtest":
##        zout = zipfile.ZipFile(dir + ".xpi", "w")
##        make_archive(os.path.curdir + "/fbtest/branches/" + dir, zout)
##        zout.close()

# Get the tests and testlists from directory
if not os.path.isdir(os.path.curdir + "/getfirebug.com/tests/.svn"):
    client.checkout("http://fbug.googlecode.com/svn/tests/", os.getcwd() + "/getfirebug.com/tests")
else:
    client.update(os.path.curdir + "/getfirebug.com/tests")
os.system("wget -N http://getfirebug.com/tests/issues/issue1205/中文 以及空格.html")
os.system("cp -r -u " + os.getcwd() + "/getfirebug.com/tests " + serverpath)



