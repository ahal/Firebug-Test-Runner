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
# Bob Clary.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
# Bob Clary
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
    
    resultCount = 0
    lastResultDoc = None

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
                    if not "OS Name" in testheaderdoc:
                        testheaderdoc["OS Name"] = platform["name"]

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
                    resultCount += 1
                    lastResultDoc = dict(testresultdoc)
                    couchdb.create(testresultdoc)
                    if "progress" in testresultdoc:
                        del(testresultdoc["progress"])

    if resultCount < int(lastResultDoc["Total Tests"]):
        print "[Info] Possible crash detected"
        lastResultDoc["type"] = "crash"
        lastResultDoc["tests run"] = str(resultCount)
        couchdb.create(lastResultDoc)
        
    logfilehandle.close()
    return 0

if __name__ == '__main__':
    main(sys.argv[1:])