import fb_run, ConfigParser, os, subprocess, sys, optparse, urllib2

def retrieve_url(url, filename):
    ret = urllib2.urlopen(url)
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()

def get_changeset(build):
    curdir = os.getcwd()
    if build == "1.9.2":
        os.chdir("/work/mozilla/builds/hg.mozilla.org/mozilla-1.9.2")
    elif build == "1.9.3":
        os.chdir("/work/mozilla/builds/hg.mozilla.org/mozilla-central")
    else:
        return "0"
    subprocess.call("hg pull && hg update", shell=True, env={"PATH":"/usr/local/bin",})
    proc = subprocess.Popen("hg tip", shell=True, stdout=subprocess.PIPE, env={"PATH":"/usr/local/bin",})
    changeset = proc.communicate()[0]
    os.chdir(curdir)
    # Extract the actual changeset from the output
    return changeset[changeset.index(":", changeset.index(":") + 1) + 1:changeset.index("\n")]
    
def build_needed(build):
    # Find new changeset
    new_changeset = get_changeset(build)
    # Create the changesets file if it doesn't exist
    if not os.path.exists("changesets"):
        file = open("changesets", "w")
        file.close()
    # Read in changesets
    cs = ConfigParser.ConfigParser()
    cs.read("changesets")        
    if cs.has_section(build):
        old_changeset = cs.get(build, "changeset")
        if old_changeset == new_changeset:
            return False
    else:
        cs.add_section(build)
    cs.set(build, "changeset", new_changeset)
    file = open("changesets", "w")
    cs.write(file)
    file.close()
    return True

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
    
    # Lookup table mapping firefox versions to builds
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : '1.9.3' }
    # Download test-bot.config to see which versions of Firefox to run the FBTests against
    retrieve_url(opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "test-bot.config", "test-bot.config")
    
    config = ConfigParser.ConfigParser()
    config.read("test-bot.config")
    
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    # For each version of Firefox, see if it needs to be rebuilt and call fb_run to run the tests
    for build in builds:
        build = lookup[build]
        
        if build_needed(build):
            subprocess.call("$TEST_DIR/bin/builder.sh -p firefox -b " + build + " -T debug -B 'clobber checkout build'", shell=True, env={"TEST_DIR":"/work/mozilla/builds/hg.mozilla.org/sisyphus",})

        # Run fb_run.py with argv
        argv[len(argv) - 3:] = ["/work/mozilla/builds/" + build + "/mozilla/firefox-debug/dist/bin/firefox"]
        argv[len(argv) - 1:] = [get_changeset(build)]
        fb_run.main(argv)
    
if __name__ == '__main__':
    main(sys.argv[1:])