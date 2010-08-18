#!/usr/bin/env python

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
# The Original Code is mozilla.org code.
# 
# The Initial Developer of the Original Code is
# Mozilla.org.
# Portions created by the Initial Developer are Copyright (C) 2010
# the Initial Developer. All Rights Reserved.
# 
# Contributor(s):
#     Jeff Hammel <jhammel@mozilla.com>     (Original author)
# 
# Alternatively, the contents of this file may be used under the terms of
# either of the GNU General Public License Version 2 or later (the "GPL"),
# or the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
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

import lxml.html
import re
import sys
import platform

if platform.system().lower() == "windows":
    REGEX = re.compile(r'firefox-.*\.en-US\.linux-(i686|x86_64)\.tar\.bz2')
elif platform.system().lower() == "linux":
    REGEX = re.compile(r'firefox-.*\.en-US\.linux-(i686|x86_64)\.tar\.bz2')
else:
    REGEX = re.compile(r'firefox-.*\.en-US\.linux-(i686|x86_64)\.tar\.bz2')

def builds(url):
  element = lxml.html.parse(url)
  links = element.xpath('//a[@href]')
  builds = {}
  url = url.rstrip('/')
  for link in links:
    target = link.get('href').strip('/')
    name = link.text.strip('/')
    if name != target:
      continue
    try:
      builds[int(name)] = '%s/%s/' % (url, name)
    except ValueError:
      pass
  return builds

def latest_build_url(url):
  _builds = builds(url)
  latest = max(_builds.keys())
  build_info = _builds[latest]
  element = lxml.html.parse(build_info)
  links = element.xpath('//a[@href]')
  for link in links:
    href = link.get('href')
    if REGEX.match(href):
      return '%s/%s' % (build_info.rstrip('/'), href)

def platform():
  """returns string of platform, as displayed for buildbot builds"""
  # XXX this should use the same code as buildbot
  bits, linkage = platform.architecture()
  os = platform.system.lower()
  print os + " " + bits
  if os == 'linux' or os == 'linux2':
    return 'linux' + (bits if bits=='64' else '')
  elif os == 'windows' or os == 'win32':
    return 'win' + bits
  elif os == 'darwin' or os == 'macosx':
    return 'macosx' + (bits if bits=='64' else '')
  else:
    raise NotImplementedError

def main(args=sys.argv[1:]):

  # parse options
  from optparse import OptionParser
  parser = OptionParser()
  parser.add_option('-d', '--debug', dest='debug', 
                    action='store_true', default=False,
                    help="get a debug build")
  try:
    client_platform = platform()
  except NotImplementedError:
    client_platform = None
  platform_help = 'platform (linux, linux64, win32, macosx, macosx64, etc)'
  if client_platform:
    platform_help += ' [DEFAULT: %s]' % client_platform
  parser.add_option('-p', '--platform', dest='platform',
                    default=client_platform, help=platform_help)
  parser.add_option('--product', dest='product', default='mozilla-central',
                    help="product [DEFAULT: mozilla-central]")
  options, args = parser.parse_args(args)

  # check parsed options
  if not options.platform:
    parser.error('Specify your platform')

  # build the base URL
  BASE_URL = 'http://stage.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-central-linux/'
  BASE_URL = 'http://stage.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/'
  BASE_URL += options.product + '-' + options.platform
  if options.debug:
    BASE_URL += '-debug'
  BASE_URL += '/'

  return latest_build_url(BASE_URL)

if __name__ == '__main__':
  main()

