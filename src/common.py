#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-03-21
#

"""
"""

from __future__ import print_function, unicode_literals

import sys
import os
import re


PACKAL_PIDFILE = 'packal.pid'
LOCAL_PIDFILE = 'local.pid'
CACHE_MAXAGE = 600

STATUS_UNKNOWN = -1  # not on Packal
STATUS_UP_TO_DATE = 0  # current version installed
STATUS_UPDATE_AVAILABLE = 1  # newer version on Packal
STATUS_SPLITTER = 2  # on Packal, but not installed from there


class Version(object):
    """Parse string version numbers into integers and make them comparable"""

    @classmethod
    def parse_version(self, version_string):
        """Parse a string of form `n.nn.n` into a tuple of integers"""
        components = re.split(r'\D', version_string)
        digits = []
        for s in components:
            try:
                digits.append(int(s))
            except ValueError:
                continue
        return tuple(digits)

    def __init__(self, version_string):
        self.version_string = version_string
        self.version_tuple = self.parse_version(version_string)

    def __cmp__(self, other):
        if self.version_tuple == other.version_tuple:
            return 0
        if self.version_tuple > other.version_tuple:
            return 1
        if self.version_tuple < other.version_tuple:
            return -1

    def __str__(self):
        return repr(self.version_tuple)

    __repr__ = __str__


def process_exists(pidfile):
    """Return True is ``pidfile`` exists and contains a valid PID"""
    if os.path.exists(pidfile):
        pid = int(open(pidfile, 'rb').read())
        try:
            os.kill(pid, 0)
        except OSError:  # invalid PID
            return False
        return True
    return False


def daemonise(stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
    """This forks the current process into a daemon.
    The stdin, stdout, and stderr arguments are file names that
    will be opened and be used to replace the standard file descriptors
    in sys.stdin, sys.stdout, and sys.stderr.
    These arguments are optional and default to /dev/null.
    Note that stderr is opened unbuffered, so
    if it shares a file with stdout then interleaved output
    may not appear in the order that you expect.

    """

     # Do first fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # Exit first parent.
    except OSError as err:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (err.errno,
                                                        err.strerror))
        sys.exit(1)
    # Decouple from parent environment.
    os.chdir("/")
    os.umask(0)
    os.setsid()
    # Do second fork.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)  # Exit second parent.
    except OSError as err:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (err.errno,
                                                        err.strerror))
        sys.exit(1)
    # Now I am a daemon!
    # Redirect standard file descriptors.
    si = open(stdin, 'r', 0)
    so = open(stdout, 'a+', 0)
    se = open(stderr, 'a+', 0)
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())
