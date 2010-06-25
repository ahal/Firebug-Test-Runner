import couchquery, dirtyutils
import re, sys
from optparse import OptionParser


def main(argv):
    usage = '''
%prog --couch http://couchserver --database databasename --log logfile
'''
    parser = OptionParser(usage=usage)

    parser.add_option('--couch', action='store', type='string',
                      dest='couchserveruri',
                      default='http://127.0.0.1:5984',
                      help='uri to crashtest couchdb server')

    parser.add_option('--database', action='store', type='string',
                      dest='databasename',
                      default='firebug',
                      help='database name. defaults to firebug.')

    parser.add_option('--logfile', action='store', type='string',
                      dest='logfilename',
                      help='log file path.')
                    
    parser.add_option('--changeset', action='store', type='string',
                      dest='changeset',
                      default='unspecified',
                      help='changeset of build the test was run against.')

    (options, args) = parser.parse_args(argv)

    platform = dirtyutils.get_platform()

    couchdb = couchquery.Database(options.couchserveruri + '/' + options.databasename)

    if not options.logfilename:
        parser.print_help()
        exit(1)

    reFirebugMeta = re.compile(r'^FIREBUG INFO \| ([^|:]*): (.*)') # 1: metadata item, 2: value
    
    reFirebugProgress = re.compile(r'^FIREBUG INFO \| ([^ ]*) \| ((\[OK\]|\[ERROR\]) .*)') # 1: file, 2: progress info
    reFirebugStart = re.compile(r'^FIREBUG INFO \| ([^ ]*) \| \[START\] (.*)') # 1: file, 2: description
    reFirebugResult = re.compile(r'^FIREBUG (TEST-[^ ]*) \| .*DONE') # 1: result

    checkForMeta = True
    testheaderdoc = {"type" : "header"}
    testresultdoc = None
    testprogressinfo = ""

    logfilehandle = open(options.logfilename, 'r')
    for logline in logfilehandle:
        logline = logline.rstrip('\n')

        match = reFirebugProgress.match(logline)
        if match:
            testprogressinfo += match.group(2) + "\n"
        else:
            if checkForMeta:
                match = reFirebugMeta.match(logline)
                if match:
                    #print 'test: meta: %s=%s' % (match.group(1), match.group(2))
                    testheaderdoc[match.group(1)] = match.group(2)
                    testheaderdoc["App Changeset"] = options.changeset
                    testheaderdoc["CPU Architecture"] = platform["cpu"]
                    testheaderdoc["OS Detailed Name"] = platform["version"]

            match = reFirebugStart.match(logline)
            if match:
                if checkForMeta:
                    headerinfo = couchdb.create(testheaderdoc)
                checkForMeta = False
                #print 'test: testfile=%s, testdescription=%s' % (match.group(1), match.group(2))
                testresultdoc = dict(testheaderdoc)
                testresultdoc["headerid"] = headerinfo["id"]
                testresultdoc["type"] = "result"
                testresultdoc["file"] = match.group(1)
                testresultdoc["description"] = match.group(2)
            else:
                match = reFirebugResult.match(logline)
                if match:
                    #print 'test: result=%s' % match.group(1)
                    testresultdoc["result"] = match.group(1)
                    if testprogressinfo != "":
                        testresultdoc["progress"] = testprogressinfo
                        testprogressinfo = ""
                    couchdb.create(testresultdoc)
                    if "progress" in testresultdoc:
                        del(testresultdoc["progress"])

    logfilehandle.close()
    return 0

if __name__ == '__main__':
    main(sys.argv[1:])