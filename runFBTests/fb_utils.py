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
from ConfigParser import ConfigParser
import datetime
import urllib2
import platform

# This is a quick hack that will rarely be used
# It is here so we don't have to depend on an entire RDF parsing module
def parse_rdf(self, lines, tagname):
    """
    Parse a list of rdf formated text
    and return the value of 'tagname'
    """
    for line in lines:
        if line.find("<em:" + tagname + ">") != -1:
            return line[line.find(">") + 1:line.rfind("<")]
    return -1
    
def create_log(profile, binary, testlist):
    """
    In the event that the FBTests fail to run and no log file is created,
    create our own to send to the database.
    """
    try:
        content = []
        logfile = open(os.path.join(profile, "extensions/firebug@software.joehewitt.com/install.rdf"))
        content.append("FIREBUG INFO | Firebug: " + parse_rdf(logfile.readlines(), "version") + "\n")
        logfile = open(os.path.join(profile, "extensions/fbtest@mozilla.com/install.rdf"))
        content.append("FIREBUG INFO | FBTest: " + parse_rdf(logfile.readlines(), "version") + "\n")
        parser = ConfigParser()
        parser.read(os.path.join(os.path.dirname(binary), "application.ini"))
        content.append("FIREBUG INFO | App Name: " + parser.get("App", "Name") + "\n")
        content.append("FIREBUG INFO | App Version: " + parser.get("App", "Version") + "\n")
        content.append("FIREBUG INFO | App Platform: " + parser.get("Gecko", "MaxVersion") + "\n")
        content.append("FIREBUG INFO | App BuildID: " + parser.get("App", "BuildID") + "\n")
        content.append("FIREBUG INFO | Export Date: " + datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT") + "\n")
        content.append("FIREBUG INFO | Test Suite: " + testlist + "\n")
        content.append("FIREBUG INFO | Total Tests: 0\n")
        content.append("FIREBUG INFO | Fail | [START] Could not start FBTests\n")
        logfile = open(os.path.join(profile, "firebug/firebug-test.log"), "w")        
        logfile.writelines(content)
        return logfile
    except Exception as e:
        print "[Warn] Failed to synthesize log file: " + str(e)

def download(url, savepath):
    """
    Save the file located at 'url' into 'filename'
    """
    ret = urllib2.urlopen(url)
    savedir = os.path.dirname(savepath)
    if savedir and not os.path.exists(savedir):
        os.makedirs(savedir)
    outfile = open(filename, 'wb')
    outfile.write(ret.read())
    outfile.close()
    
def get_changeset(buildpath):
    """
    Return the changeset of the build located at 'buildpath'
    """
    app_ini = ConfigParser()
    appPath = os.path.join(buildpath, ("Contents/MacOS" if platform.system().lower() == "darwin" else ""))
    app_ini.read(os.path.join(appPath, "application.ini"))
    return app_ini.get("App", "SourceStamp")
