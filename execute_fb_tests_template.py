from time import sleep
import fb_run, ConfigParser, os, sys, optparse, urllib2, get_latest, tarfile, shutil, dirtyutils

# Global changeset variable
changeset = {}

def retrieve_url(url, filename):
    try:
        ret = urllib2.urlopen(url)
    except:
        return -1
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()
    return 0

def get_changeset(buildpath):
    app_ini = ConfigParser.ConfigParser()
    app_ini.read(os.path.join(buildpath, "application.ini"))
    return app_ini.get("App", "SourceStamp")
    
def build_needed(build, buildpath):
    # Find new changeset
    new_changeset = get_changeset(buildpath)
    global changeset
    if not build in changeset:
        changset[build] = -1
    if changeset[build] != new_changeset:
        changeset[build] = new_changeset
        return True
    return False

def run_builds(argv, opt):
    # Lookup table mapping firefox versions to builds
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : '1.9.3', '4.0' : '2.0.0' }
    # Download test-bot.config to see which versions of Firefox to run the FBTests against
    if retrieve_url(opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "test-bot.config", "test-bot.config") != 0:
        return "[Error] Could not download 'test-bot.config' from '" + opt.serverpath + "'"

    platform = dirtyutils.get_platform()
    
    config = ConfigParser.ConfigParser()
    config.read("test-bot.config")
    
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    # For each version of Firefox, see if it needs to be rebuilt and call fb_run to run the tests
    for build in builds:
        build = lookup[build]
        print "[Info] Running Firebug" + opt.version + " tests against Mozilla " + build

        # Scrape for the latest tinderbox build and extract it to the tmp directory
        retrieve_url(get_latest.main(["--product=mozilla-" + (build if build != "1.9.3" else "central")]), "/tmp/mozilla-" + build + ".tar.bz2")
        tar = tarfile.open(os.path.join("/tmp/mozilla-" + build + ".tar.bz2"))
        tar.extractall(os.path.join("/tmp/mozilla-" + build))
        tar.close()
        if build_needed(build, "/tmp/mozilla-" + build + "/firefox/"):
            # Run fb_run.py with argv
            global changeset
            argv[-3] = os.path.join("/tmp/mozilla-" + build + "/firefox/firefox")
            argv[-1] = changeset[build]
            ret = fb_run.main(argv)
            if ret != 0:
                print ret
        # Remove build directories
        os.remove(os.path.join("/tmp/mozilla-" + build + ".tar.bz2"))
        shutil.rmtree(os.path.join("/tmp/mozilla-" + build))
    return 0

def main(argv):
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-p", "--profile", dest="profile", help="The profile to use when running Firefox")
    parser.add_option("-s", "--serverpath", dest="serverpath", help="The http server containing the fb tests")
    parser.add_option("-v", "--version", dest="version", help="The firebug version to run")
    parser.add_option("-c", "--couch", dest="couchserveruri", help="URI to couchdb server for log information")
    parser.add_option("-d", "--database", dest="databasename", help="Database name to keep log information")
    parser.add_option("-t", "--testlist", dest="testlist", help="Testlist to use. Should use default")
    (opt, remainder) = parser.parse_args(argv)
    # Synthesize arguments to be passed to fb_run
    argv.append("-b")
    argv.append("buildpath")        # Placeholder
    argv.append("--changeset")
    argv.append("changeset")        # Placeholder
    
    while True:
        print "[Info] Starting builds and FBTests for Firebug" + opt.version
        ret = run_builds(argv, opt)
        if ret != 0:
            print ret
        print "[Info] Sleeping for 1 hour"
        sleep(3600)
        
    
if __name__ == '__main__':
    main(sys.argv[1:])