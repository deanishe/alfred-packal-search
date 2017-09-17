#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-04-07
#

"""update_workflows.py [--force-update]

Usage:
    update_workflows.py [--force-update]
"""

from __future__ import print_function, unicode_literals

import subprocess
import sys
import os
from datetime import datetime
from plistlib import readPlist, readPlistFromString

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

from workflow import web, Workflow

from common import (CACHE_MAXAGE, Version, STATUS_SPLITTER, STATUS_UNKNOWN,
                    STATUS_UPDATE_AVAILABLE, STATUS_UP_TO_DATE,
                    STATUS_NOT_INSTALLED)

log = None

MANIFEST_URL = 'https://raw.github.com/packal/repository/master/manifest.xml'
# WORKFLOW_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALFRED_PREFS = os.path.expanduser(
    '~/Library/Preferences/com.runningwithcrayons.Alfred-Preferences-3.plist')


class Constant(object):

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return 'Constant({0:r})'.format(self.value)

    def __str__(self):
        return str(self.value)


NOT_INSTALLED = Constant('NOT INSTALLED')


def read_plist(path):
    """Convert plist to XML and read its contents."""
    cmd = [b'plutil', b'-convert', b'xml1', b'-o', b'-', path]
    xml = subprocess.check_output(cmd)
    return readPlistFromString(xml)


def get_workflow_directory():
    """Return path to Alfred's workflow directory."""
    prefs = read_plist(ALFRED_PREFS)
    syncdir = prefs.get('syncfolder')

    if not syncdir:
        log.debug('Alfred sync folder not found')
        return None

    syncdir = os.path.expanduser(syncdir)
    wf_dir = os.path.join(syncdir, 'Alfred.alfredpreferences/workflows')
    log.debug('Workflow sync dir : %r', wf_dir)

    if os.path.exists(wf_dir):
        log.debug('Workflow directory retrieved from Alfred preferences')
        return wf_dir

    log.debug('Alfred.alfredpreferences/workflows not found')
    return None


def packal_metadata(xmlpath):
    """Return ``dict`` of metadata in ``package.xml`` file created by Packal"""
    tree = ET.parse(xmlpath)
    root = tree.getroot()
    data = {}
    for elem in root:
        data[elem.tag] = elem.text
    data['version'] = Version(data['version'])
    return data


def get_installed_workflows():
    """Return ``dict`` of installed workflows
    ``{bundleid : version}``

    ``version`` is ``None`` if workflow isn't from Packal.org
    """
    workflows = {}
    workflow_dir = get_workflow_directory()

    log.debug('reading workflows installed in %r ...', workflow_dir)
    for name in os.listdir(workflow_dir):
        path = os.path.join(workflow_dir, name)
        if not os.path.isdir(path):
            continue

        info_plist = os.path.join(path, 'info.plist')
        packal_xml = os.path.join(path, 'packal', 'package.xml')
        if not os.path.exists(info_plist):
            continue

        try:
            bundleid = readPlist(info_plist)['bundleid']
            if not bundleid:
                log.warning('no bundleid in info.plist : %s', path)
                continue
        except Exception as err:
            log.error('bad info.plist in workflow %r: %s', path, err)
            continue

        try:
            metadata = {'version': None, 'bundle': bundleid}
            if os.path.exists(packal_xml):
                metadata.update(packal_metadata(packal_xml))
        except Exception as err:
            log.error('bad packal/package.xml in workflow %r: %s', path, err)
            continue

        workflows[metadata['bundle']] = metadata['version']

    log.debug('%d workflows installed locally', len(workflows))
    return workflows


def get_packal_workflows():
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

    log.debug('{} workflows available on Packal.org'.format(len(workflows)))
    return workflows


def get_workflows():
    """Return list of workflows on on Packal.org with update status."""
    local_workflows = get_installed_workflows()
    packal_workflows = get_packal_workflows()
    for packal_workflow in packal_workflows:
        # set version number
        bundle = packal_workflow.get('bundle')
        local_version = local_workflows.get(bundle, NOT_INSTALLED)
        packal_version = packal_workflow['version']
        log.debug('workflow `{0}` packal : {1}  local : {2}'.format(
                  packal_workflow['bundle'],
                  packal_workflow['version'],
                  local_version))
        # log.debug('local version : {0}'.format(local_version))

        if local_version is NOT_INSTALLED:
            packal_workflow['status'] = STATUS_NOT_INSTALLED
        elif not local_version:
            packal_workflow['status'] = STATUS_SPLITTER
        elif packal_version > local_version:
            packal_workflow['status'] = STATUS_UPDATE_AVAILABLE
        elif packal_version == local_version:
            packal_workflow['status'] = STATUS_UP_TO_DATE
        else:
            packal_workflow['status'] = STATUS_UNKNOWN
    return packal_workflows


def main(wf):
    from docopt import docopt
    args = docopt(__doc__, argv=wf.args)
    if args.get('--force-update'):
        max_age = 1
        log.debug('Forcing update of Packal workflows')
    else:
        max_age = CACHE_MAXAGE

    wf.cached_data('workflows', get_workflows,  max_age=max_age)


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    sys.exit(wf.run(main))
