# Firebug Test Runner

This module intends to automate the process of running the [Firebug tests](http://getfirebug.com/wiki/index.php/Firebug_Tests)
which can be [downloaded and installed here](http://getfirebug.com/releases/fbtest/)
The module examines data stored by the Firebug team in a file on their servers to determine which versions
of the Firebug tests to run against which versions of Firefox.  The module then downloads the latest
tinderbox builds of those Firefox versions, runs the tests and sends the results to the specified
database.

## Installation

### Dependencies
The Firebug Test Runner uses lxml which requires the following packages to be installed: python-dev, libxslt1-dev and libxml2

On Debian

    sudo apt-get install python-dev libxml2 libxslt1-dev

On OSX (package names may be slightly different)

    sudo port install python-dev libxml2 libxslt1-dev

On Windows it is a bit trickier. I'd recommend installing the [executable directly](http://pypi.python.org/pypi/lxml/2.3)


### Install from distribute
Make sure you have [distribute](http://pypi.python.org/pypi/distribute) installed 

    easy_install pip
    pip install runFBTests

Into a [virtualenv](http://pypi.python.org/pypi/virtualenv) of course! :)


### Install from source 
From the repo root and into a [virtualenv](http://pypi.python.org/pypi/virtualenv), simply run:

    python setup.py install

Or if you are doing development work and don't want to run the above command everytime you make a change:

    python setup.py develop

## Usage

There are two parts to the Firebug-Test-Runner, a runner and an updater.

### Running Tests
The runner takes a serverpath as an argument and runs the tests found on that server. The server has to be 
set up in a certain way (which is where the updater comes in). By default the server is http://getfirebug.com

To run the tests use:

    runFBTests --serverpath server_url --couch couch_server --database database_name

For a full list of commands use:

    runFBTests --help


### Updating Tests
It is perfectly fine to use http://getfirebug.com as the server, but you may want more control over which 
test versions are run and so you may wish to set up your own server.

On this server you need to run the updateFBTests script to pull the latest repos and tests from the firebug 
repository. It will ensure that the correct versions of Firebug are run against the correct versions of the 
tests.

Use:

    updateFBTests -d path_to_document_root


For more options run:

    updateFBTests --help

## Results

Current results of three VM's running this module are posted here:
http://getfirebug.com/testresults?dburi=http://firebug.couchone.com

