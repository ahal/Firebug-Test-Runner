== Firebug Test Runner ==

This module intends to automate the process of running the Firebug tests (https://getfirebug.com/tests/)
which can be downloaded and installed here: http://getfirebug.com/releases/fbtest/

The module examines data stored by the Firebug team in a file on their servers to determine which versions
of the Firebug tests to run against which versions of Firefox.  The module then downloads the latest
tinderbox builds of those Firefox versions, runs the tests and sends the results to the specified
database.

To run the tests use the 'runFBTests' command with the desired options.

By default the module uses the test files hosted at http://getfirebug.com/tests, but users are able to 
specify their own server if desired.  For this case, they should use the
'updateFBTests -d path_to_document_root' command.

Current results of three VM's running this module are posted here:
http://getfirebug.com/testresults

# Installation

The Firebug Test Runner uses lxml which requires the following packages to be installed: python-dev, libxslt1-dev and libxml2


To install simply run 'python setup.py install' (into a virtualenv of course!)
