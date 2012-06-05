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
# The Original Code is Mozilla Corporation Code.
#
# The Initial Developer of the Original Code is
# Andrew Halberstadt.
# Portions created by the Initial Developer are Copyright (C) 2008
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#  Andrew Halberstadt <ahalberstadt@mozilla.com>
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

from setuptools import setup, find_packages
import sys

desc = """Scripts for running the Firebug Unit Tests against various Mozilla builds"""
summ = """This tool will allow you to automate the process of running the Firebug test suite in
a variety of different configurations."""

PACKAGE_NAME = "runFBTests"
PACKAGE_VERSION = "1.2.1"

deps = ["mozrunner >= 4.1",
        "mozlog >= 1.0",
        "couchquery >= 0.9",
        "getlatesttinderbox >= 0.2.5",]

setup(name=PACKAGE_NAME,
      version=PACKAGE_VERSION,
      description=desc,
      long_description=summ,
      author='Andrew Halberstadt, Mozilla',
      author_email='halbersa@gmail.com',
      url='http://github.com/ahal/Firebug-Test-Runner',
      license='MPL 1.1/GPL 2.0/LGPL 2.1',
      packages=find_packages(exclude=['legacy']),
      include_package_data=False,
      entry_points="""
          [console_scripts]
          runFBTests = runFBTests:cli_run
          updateFBTests = runFBTests:cli_update
        """,
      platforms =['Any'],
      install_requires = deps,
      classifiers=['Environment :: Console',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Mozilla Public License 1.1 (MPL 1.1)',
                   'Natural Language :: English',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: POSIX :: Linux',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                   'Topic :: Software Development :: Testing',
                  ]
     )
