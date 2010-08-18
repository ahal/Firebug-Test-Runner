import platform
import urllib
import csv
import sys
import re
import os

def path(*a):
    ROOT = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ROOT, *a)

def download(url, dest=None):
    web_file = urllib.urlopen(url)

    if not dest:
        dest = os.path.basename(url)

    local_file = open(dest, 'wb')
    local_file.write(web_file.read())
    web_file.close()
    local_file.close()
    return dest

def read_csv(file_name, delimiter=","):
    reader = csv.reader(open(file_name, "r"), delimiter=delimiter)
    return list(reader)

def get_platform():
    uname = platform.uname()
    name = uname[0]
    version = uname[2]

    if name == "Linux":
        (distro, version, codename) = platform.linux_distribution()
        version = distro + " " + version
    elif name == "Darwin":
        name = "Mac"
        (release, versioninfo, machine) = platform.mac_ver()
        version = "OS X " + release

    bits = platform.architecture()[0]
    cpu = uname[4]
    if cpu == "i386" or cpu == "i686":
        if bits == "32bit":
            cpu = "x86"
        elif bits == "64bit":
            cpu = "x86_64"
    elif cpu == 'Power Macintosh':
        cpu = 'ppc'

    bits = re.compile('(\d+)bit').search(bits).group(1)

    return {'name': name, 'version': version, 'bits':  bits, 'cpu': cpu}

def major_version(version):
    return re.compile('((\d+).(\d+)).*$').search(version).group(1)


