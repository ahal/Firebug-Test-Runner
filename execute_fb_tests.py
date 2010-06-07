import fb_run, ConfigParser, os, subprocess, sys, optparse, urllib2

def retrieve_url(url, filename):
    ret = urllib2.urlopen(url)
    output = open(filename, 'wb')
    output.write(ret.read())
    output.close()

def main(argv):
    usage = "%prog [options]"
    parser = optparse.OptionParser(usage)
    parser.add_option("-v", "--version", dest="version", default="1.6", help="The firebug version to run")
    parser.add_option("-s", "--serverpath", dest="serverpath", default="http://localhost/", help="Server containing test-bot.config")
    (opt, remainder) = parser.parse_args(argv)
    
    lookup = { '3.5' : '1.9.1', '3.6' : '1.9.2', '3.7' : '1.9.3' }
    retrieve_url(opt.serverpath + ("" if opt.serverpath[-1] == "/" else "/") + "test-bot.config", "test-bot.config")
    
    config = ConfigParser.ConfigParser()
    config.read("test-bot.config")
    builds = config.get("Firebug" + opt.version, "FIREFOX_VERSION").split(",")
    for build in builds:
        build = lookup[build]
        subprocess.call("/work/mozilla/builds/hg.mozilla.org/sisyphus/bin/builder.sh -p firefox -b " + build + " -T debug -B 'clobber checkout build'", shell=True)
        fb_run.main(['-b', '/work/mozilla/builds/' + build + '/mozilla/firefox-debug/dist/bin/firefox'])
        
    
    config.close()
    
    
if __name__ == '__main__':
    main(sys.argv[1:])