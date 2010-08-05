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

from time import sleep
import fb_run, ConfigParser, os, sys, optparse, urllib2, get_latest, tarfile, shutil

# Global changeset variable
changeset = {}

# Clean the temporary folder
def clean_temp_folder(basedir):
    try:
        for filename in os.listdir(basedir):
            if os.isdir(os.path.join(basedir, filename)) and filename[0:3] == "tmp":
                shutil(os.path.join(basedir,filename))
    except:
        return -1

# Save the file located at 'url' into 'filename'
def retrieve_url(url, filename):
    try:
        ret = urllib2.urlopen(url)
    except:
        return -1
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()
    return 0

# Return the changeset of the build located at 'buildpath'
def get_changeset(buildpath):
    app_ini = ConfigParser.ConfigParser()
    app_ini.read(os.path.join(buildpath, "application.ini"))
    return app_ini.get("App", "SourceStamp")

# Return False if the tests have never been run against the current changeset of 'build'
# True otherwise
def build_needed(build, buildpath):
    # Find new changeset
    new_changeset = get_changeset(buildpath)
    global changeset
    if not build in changeset:
        changeset[build] = -1
    if changeset[build] != new_changeset:
        changeset[build] = new_changeset
        return True
    return False

def run_builds(argv, opt, basedir):
    # Lookup table mapping firefox versions to builds
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : '1.9.3', '4.0' : '2.0.0' }
    # Download test-bot.config to see which versions of Firefox to run the FBTests against
    if retrieve_url(opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "test-bot.config", "test-bot.config") != 0:
        return "[Error] Could not download 'test-bot.config' from '" + opt.serverpath + "'"
    
    config = ConfigParser.ConfigParser()
    config.read("test-bot.config")
    
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    # For each version of Firefox, see if it needs to be rebuilt and call fb_run to run the tests
    for build in builds:
        build = lookup[build]
        print "[Info] Running Firebug" + opt.version + " tests against Mozilla " + build

        try:
            # Scrape for the latest tinderbox build and extract it to the tmp directory
            retrieve_url(get_latest.main(["--product=mozilla-" + (build if build != "1.9.3" else "central")]), os.path.join(basedir, "mozilla-" + build + ".tar.bz2"))
            tar = tarfile.open(os.path.join(basedir, "mozilla-" + build + ".tar.bz2"))
            tar.extractall(os.path.join(basedir, "mozilla-" + build))
            tar.close()
        except IOError:
            return "[Error] Could not grab the latest tinderbox build"
        if build_needed(build, os.path.join(basedir, "mozilla-" + build + "/firefox/")):
            # Run fb_run.py with argv
            global changeset
            argv[-3] = os.path.join(basedir, "mozilla-" + build + "/firefox/firefox")
            argv[-1] = changeset[build]
            ret = fb_run.main(argv)
            if ret != 0:
                print ret
        # Remove build directories
        os.remove(os.path.join(basedir, "mozilla-" + build + ".tar.bz2"))
        shutil.rmtree(os.path.join(basedir, "mozilla-" + build))
    return 0

def main(argv):
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-p", "--profile", dest="profile",
                      help="The profile to use when running Firefox")
                        
    parser.add_option("-s", "--serverpath", dest="serverpath",
                      help="The http server containing the fb tests")
                        
    parser.add_option("-v", "--version", dest="version",
                      help="The firebug version to run")
                        
    parser.add_option("-c", "--couch", dest="couchserveruri",
                      help="URI to couchdb server for log information")
                        
    parser.add_option("-d", "--database", dest="databasename",
                      help="Database name to keep log information")
                        
    parser.add_option("-t", "--testlist", dest="testlist",
                      help="Testlist to use. Should use default")
    (opt, remainder) = parser.parse_args(argv)
    # Synthesize arguments to be passed to fb_run
    argv.append("-b")
    argv.append("buildpath")        # Placeholder
    argv.append("--changeset")
    argv.append("changeset")        # Placeholder
    
    basedir = "/tmp"
    
    i = 0
    while True:
        print "[Info] Starting builds and FBTests for Firebug" + opt.version
        ret = run_builds(argv, opt, basedir)
        if ret != 0:
            print ret
        if i % 12 == 0:
            clean_temp_folder(basedir)
        i += 1
        print "[Info] Sleeping for 4 hour"
        sleep(14400)
        
    
if __name__ == '__main__':
    main(sys.argv[1:])