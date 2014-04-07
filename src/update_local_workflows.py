#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-03-21
#

"""update_local_workflows.py [--force-update]

Usage:
    update_local_workflows.py [--force-update]
"""

from __future__ import print_function, unicode_literals

import sys
import os
from plistlib import readPlist
try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from workflow import Workflow
from common import (Version, process_exists, daemonise,
                    LOCAL_PIDFILE, CACHE_MAXAGE)

log = None

# set this before daemonising
WORKFLOW_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def packal_metadata(xmlpath):
    """Return ``dict`` of metadata in ``package.xml`` file created by Packal"""
    tree = ET.parse(xmlpath)
    root = tree.getroot()
    data = {}
    for elem in root:
        data[elem.tag] = elem.text
    data['version'] = Version(data['version'])
    return data


def installed_workflows(wfdir):
    """Return ``dict`` of installed workflows
    ``{bundleid : version}``

    ``version`` is ``None`` if workflow isn't from Packal.org
    """
    workflows = {}
    for name in os.listdir(wfdir):
        path = os.path.join(wfdir, name)
        if not os.path.isdir(path):
            continue
        info_plist = os.path.join(path, 'info.plist')
        packal_xml = os.path.join(path, 'packal', 'package.xml')
        if not os.path.exists(info_plist):
            continue
        bundleid = readPlist(info_plist)['bundleid']
        if not bundleid:
            print('no bundleid : {}'.format(path))
            continue
        metadata = {'version': None, 'bundleid': bundleid}
        if os.path.exists(packal_xml):
            metadata.update(packal_metadata(packal_xml))
        workflows[metadata['bundleid']] = metadata['version']
    return workflows


def main(wf):
    from docopt import docopt
    args = docopt(__doc__, argv=wf.args)
    if args.get('--force-update'):
        max_age = 1
        log.debug('Forcing update of Packal workflows')
    else:
        max_age = CACHE_MAXAGE

    pidfile = wf.cachefile(LOCAL_PIDFILE)
    if process_exists(pidfile):
        log.debug('Packal update script already running')
        return 0

    # Fork into background
    daemonise()
    # Save PID
    open(pidfile, 'wb').write('{}'.format(os.getpid()))

    log.debug('Looking for installed workflows in : {}'.format(WORKFLOW_DIR))

    def wrapper():
        return installed_workflows(WORKFLOW_DIR)

    try:
        workflows = wf.cached_data('local_workflows', wrapper,
                                   max_age=max_age)
        log.debug('{} workflows installed locally'.format(len(workflows)))
    finally:
        if os.path.exists(pidfile):
            os.unlink(pidfile)
    log.debug('Update of installed workflows finished')


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
