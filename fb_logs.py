import couchquery
import re
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

    (options, args) = parser.parse_args(argv)

    couchdb = couchquery.Database(options.couchserveruri + '/' + options.databasename)

    if not options.logfilename:
        parser.print_help()
        exit(1)

    reFirebugMeta = re.compile(r'^FIREBUG INFO \| ([^|:]*): (.*)') # 1: metadata item, 2: value

    reFirebugStart = re.compile(r'^FIREBUG INFO \| ([^ ]*) \| \[START\] (.*)') # 1: file, 2: description
    reFirebugResult = re.compile(r'^FIREBUG (TEST-[^ ]*) \| .*DONE') # 1: result

    checkForMeta = True
    testheaderdoc = {"type" : "header"}
    testresultdoc = None

    logfilehandle = open(options.logfilename, 'r')
    for logline in logfilehandle:
        logline = logline.rstrip('\n')

        #print logline

        if checkForMeta:
            match = reFirebugMeta.match(logline)
            if match:
                #print 'test: meta: %s=%s' % (match.group(1), match.group(2))
                testheaderdoc[match.group(1)] = match.group(2)

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
                couchdb.create(testresultdoc)

    logfilehandle.close()

if __name__ == '__main__':
    main(sys.argv[1:])