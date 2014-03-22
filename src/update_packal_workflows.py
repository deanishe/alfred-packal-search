#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-03-21
#

"""update_packal_workflows.py [--force-update]

Usage:
    update_packal_workflows.py [--force-update]
"""

from __future__ import print_function, unicode_literals

import sys
import os
from datetime import datetime
try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from workflow import web, Workflow
from common import (process_exists, daemonise, PACKAL_PIDFILE, CACHE_MAXAGE,
                    Version)

log = None

MANIFEST_URL = 'https://raw.github.com/packal/repository/master/manifest.xml'


def get_workflows():
    """Return list of workflows available on Packal.org"""
    workflows = []
    r = web.get(MANIFEST_URL)
    r.raise_for_status()
    manifest = ET.fromstring(r.content)
    # these elements contain multiple, |||-delimited items
    list_elements = ('categories', 'tags', 'osx')
    for workflow in manifest:
        d = {}
        for elem in workflow:
            if elem.tag in list_elements:
                if not elem.text:
                    d[elem.tag] = []
                else:
                    d[elem.tag] = [s.strip() for s in elem.text.split('|||')]
            # text elements
            elif elem.text:
                d[elem.tag] = elem.text
            else:
                d[elem.tag] = ''
        # convert timestamp to datetime
        d['updated'] = datetime.fromtimestamp(float(d['updated']))
        d['version'] = Version(d['version'])
        workflows.append(d)
    return workflows


def main(wf):
    from docopt import docopt
    args = docopt(__doc__, argv=wf.args)
    if args.get('--force-update'):
        max_age = 1
        log.debug('Forcing update of Packal workflows')
    else:
        max_age = CACHE_MAXAGE
    pidfile = wf.cachefile(PACKAL_PIDFILE)
    if process_exists(pidfile):
        log.debug('Packal update script already running')
        return 0

    # Fork into background
    daemonise()
    # Save PID
    open(pidfile, 'wb').write('{}'.format(os.getpid()))
    try:
        workflows = wf.cached_data('packal_workflows', get_workflows,
                                   max_age=max_age)
        log.debug('{} workflows on Packal'.format(len(workflows)))
    finally:
        if os.path.exists(pidfile):
            os.unlink(pidfile)
    log.debug('Update from Packal.org finished')

if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
