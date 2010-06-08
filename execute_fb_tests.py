import fb_run, ConfigParser, os, subprocess, sys, optparse, urllib2

def retrieve_url(url, filename):
    ret = urllib2.urlopen(url)
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()

def main(argv):
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-p", "--profile", dest="profile", help="The profile to use when running Firefox")
    parser.add_option("-s", "--serverpath", dest="serverpath", help="The http server containing the fb tests")
    parser.add_option("-v", "--version", dest="version", help="The firebug version to run")
    parser.add_option("-c", "--couch", dest="couchserveruri", help="URI to couchdb server for log information")
    parser.add_option("-d", "--database", dest="databasename", help="Database name to keep log information")
    (opt, remainder) = parser.parse_args(argv)
    
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : '1.9.3' }
    retrieve_url(opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "test-bot.config", "test-bot.config")
    
    config = ConfigParser.ConfigParser()
    config.read("test-bot.config")
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    for build in builds:
        build = lookup[build]
        subprocess.call("/work/mozilla/builds/hg.mozilla.org/sisyphus/bin/builder.sh -p firefox -b " + build + " -T debug -B 'clobber checkout build'", shell=True, env={"TEST_DIR":"/work/mozilla/builds/hg.mozilla.org/sisyphus",})
        fb_run.main(['-b', '/work/mozilla/builds/' + build + '/mozilla/firefox-debug/dist/bin/firefox', '-c', opt.couchserveruri, '-d', opt.database])
        
    
    config.close()
    
    
if __name__ == '__main__':
    main(sys.argv[1:])