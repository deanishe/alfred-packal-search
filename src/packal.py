#!/usr/bin/env python
# encoding: utf-8
#
# Copyright © 2014 deanishe@deanishe.net
#
# MIT Licence. See http://opensource.org/licenses/MIT
#
# Created on 2014-03-03
#

"""
Simple search of Packal.org for workflows based on the exported manifest.xml

Uses Alfred-Workflow library:
https://github.com/deanishe/alfred-workflow
"""

from __future__ import print_function, unicode_literals

import os
from datetime import datetime
from operator import itemgetter
from collections import defaultdict
import subprocess

from workflow import Workflow, ICON_WARNING, ICON_INFO
from common import (PACKAL_PIDFILE, LOCAL_PIDFILE, CACHE_MAXAGE,
                    STATUS_SPLITTER, STATUS_UNKNOWN, STATUS_UPDATE_AVAILABLE,
                    STATUS_UP_TO_DATE)

log = None

DELIMITER = '➣'

ICON_WFLOW = '/Applications/Alfred 2.app/Contents/Resources/workflowicon.icns'

STATUS_SUFFIXES = {
    STATUS_SPLITTER: '🔸',
    STATUS_UNKNOWN: '',
    STATUS_UPDATE_AVAILABLE: '❗',
    STATUS_UP_TO_DATE: '✅'
}

ITEM_ICONS = {
    'workflows': ICON_WFLOW,
    'tags': 'tag.png',
    'categories': 'category.png',
    'author': 'author.png'
}


__usage__ = """packal.py [options] <action> [<query>]

Usage:
    packal.py workflows [<query>]
    packal.py update
    packal.py tags [<query>]
    packal.py categories [<query>]
    packal.py versions [<query>]
    packal.py authors [<query>]
    packal.py open <bundleid>
    packal.py author-workflows <bundleid>
    packal.py status
"""


def run_alfred(query):
    """Call Alfred with ``query``"""
    subprocess.call([
        'osascript', '-e',
        'tell application "Alfred 2" to search "{} "'.format(query)])


def relative_time(dt):
    """Human-readable relative time, e.g. '1 hour ago'"""
    td = datetime.now() - dt
    hours = (td.days * 24.0) + (td.seconds / 3600.0)
    log.debug('{}  -->  {:0.2f} hours ago'.format(td, hours))
    minutes = int(hours * 60)
    hours = int(hours)
    days = int(hours) / 24
    if days > 60:
        return '{:d} months ago'.format(days / 30)
    elif days > 30:
        return '1 month ago'
    elif hours > 48:
        return '{:d} days ago'.format(hours / 24)
    elif hours > 23:
        return 'yesterday'
    elif hours > 1:
        return '{:d} hours ago'.format(hours)
    elif hours == 1:
        return '1 hour ago'
    else:
        return '{:d} minutes ago'.format(minutes)


def suffix_for_status(status):
    """Return ``title`` suffix for given status"""
    suffix = STATUS_SUFFIXES.get(status)
    if not suffix:
        return ''
    return ' {}'.format(suffix)


def workflow_key(workflow):
    """Return text search key for workflow"""
    # I wish tags were in the manifest :(
    elements = [workflow['name']]
    elements.extend(workflow['tags'])
    elements.extend(workflow['categories'])
    elements.append(workflow['author'])
    return ' '.join(elements)


class GoBack(Exception):
    """Raised when Workflows should back up"""


class PackalWorkflow(object):
    """Encapsulates the Workflow"""

    def __init__(self):
        self.wf = None

    def run(self, wf):
        from docopt import docopt
        self.wf = wf

        args = docopt(__usage__, argv=self.wf.args)

        self.workflows = self.wf.cached_data('packal_workflows', None,
                                             max_age=0)

        self.installed_workflows = self.wf.cached_data('local_workflows',
                                                       None, max_age=0)

        # Start update scripts if cached data is too old
        if not self.wf.cached_data_fresh('packal_workflows',
                                         max_age=CACHE_MAXAGE):
            cmd = ['python',
                   self.wf.workflowfile('update_packal_workflows.py')]
            subprocess.call(cmd)

        if not self.wf.cached_data_fresh('local_workflows',
                                         max_age=CACHE_MAXAGE):
            cmd = ['python',
                   self.wf.workflowfile('update_local_workflows.py')]
            subprocess.call(cmd)

        # Notify user if cache is being updated
        if os.path.exists(self.wf.cachefile(PACKAL_PIDFILE)):
            self.wf.add_item('Updating from Packal…',
                             valid=False, icon=ICON_INFO)
        # Notify user if installed workflow list is being updated
        if os.path.exists(self.wf.cachefile(LOCAL_PIDFILE)):
            self.wf.add_item('Updating list of installed workflows…',
                             valid=False, icon=ICON_INFO)

        if not self.workflows:
            self.wf.send_feedback()
            return 0

        self.workflows.sort(key=itemgetter('updated'), reverse=True)

        log.debug('%d workflows found in cache', len(self.workflows))

        self.query = args.get('<query>')
        self.bundleid = args.get('<bundleid>')

        for key in ('tags', 'categories', 'versions', 'authors'):
            if args.get(key):
                return self._two_stage_filter(key)

        if args.get('author-workflows'):
            return self.do_author_workflows()
        elif args.get('workflows'):
            return self._filter_workflows(self.workflows, self.query)
        elif args.get('update'):
            return self.do_update()
        elif args.get('open'):
            return self.do_open()
        elif args.get('status'):
            return self.do_status()
        else:
            raise ValueError('No action specified')

    def do_update(self):
        """Force update of cached data"""
        log.debug('Updating workflow lists...')
        try:
            subprocess.call([
                'python',
                self.wf.workflowfile('update_packal_workflows.py'),
                '--force-update'])
            subprocess.call([
                'python',
                self.wf.workflowfile('update_local_workflows.py'),
                '--force-update'])
        except Exception as err:
            log.debug('Update failed : {}'.format(err))
            print('Update failed')
            return 1
        print('Update successful')
        return 0

    def do_open(self):
        """Open Packal workflow page in browser"""
        workflow = self._workflow_by_bundleid(self.bundleid)
        log.debug('Opening : {}'.format(workflow['url']))
        subprocess.call(['open', workflow['url']])
        return 0

    def do_author_workflows(self):
        """Tell Alfred to show workflows by the same author"""
        author = self._workflow_by_bundleid(self.bundleid)['author']
        run_alfred('packal authors {} {}'.format(author, DELIMITER))
        return 0

    def do_status(self):
        """List workflows that can be updated or installed from Packal"""
        id_workflow_map = {}
        for workflow in self.workflows:
            id_workflow_map[workflow['bundle']] = workflow
        results = []
        for bundleid in self.installed_workflows:
            status = self._workflow_status(bundleid)
            if status == STATUS_SPLITTER:
                results.append((0, id_workflow_map[bundleid]['updated'],
                                id_workflow_map[bundleid]))
            elif status == STATUS_UPDATE_AVAILABLE:
                results.append((1, id_workflow_map[bundleid]['updated'],
                                id_workflow_map[bundleid]))
        results.sort(reverse=True)
        workflows = []
        for result in results:
            count, updated, workflow = result
            workflows.append(workflow)
        return self._filter_workflows(workflows, None)

    def _two_stage_filter(self, key):
        """Handle queries including ``DELIMITER``

        :attr:``~PackalWorkflow.query`` is split into ``subset`` and ``query``.
        ``subset`` is the category/tag/author/OS X version name.

        If there's only a ``subset``, show all matching workflows newest first.

        If there's a ``subset`` and a ``query``, first get workflows matching
        ``subset`` then filter them by ``query``.

        If only ``query`` is provided, search the attribute specifed by ``key``

        :param key: ``tags/categories/authors/versions``. Which attribute to
        search.
        """
        try:
            subset, query = self._split_query(self.query)
        except GoBack:
            query = 'packal {}'.format(key)
            log.debug('Going back to : {}'.format(query))
            run_alfred(query)
            return 0

        if key == 'authors':
            key = 'author'
        elif key == 'versions':
            key = 'osx'

        if subset:
            if isinstance(self.workflows[0][key], list):
                workflows = [w for w in self.workflows if subset in w[key]]
            else:
                workflows = [w for w in self.workflows if subset == w[key]]
            return self._filter_workflows(workflows, query)

        subsets = defaultdict(int)
        for workflow in self.workflows:
            if isinstance(workflow[key], list):
                for subset in workflow[key]:
                    subsets[subset] += 1
            else:
                subsets[workflow[key]] += 1

        subsets = sorted([(v, k) for (k, v) in subsets.items()], reverse=True)

        if query:
            subsets = wf.filter(query, subsets, lambda t: t[1], min_score=30)

        icon = ITEM_ICONS.get(key, ICON_WFLOW)
        for count, subset in subsets:
            wf.add_item(subset, '{} workflows'.format(count),
                        autocomplete='{} {} '.format(subset, DELIMITER),
                        icon=icon)

        wf.send_feedback()
        return 0

    def _filter_workflows(self, workflows, query):
        """Filter ``workflows`` against ``query`` and send the results
        to Alfred

        """

        if query:
            workflows = self.wf.filter(query, workflows, key=workflow_key,
                                       min_score=30)
        if not workflows:
            self.wf.add_item('Nothing found', 'Try a different query',
                             valid=False, icon=ICON_WARNING)

        for workflow in workflows:
            suffix = suffix_for_status(
                self._workflow_status(workflow['bundle']))
            title = '{}{}'.format(workflow['name'], suffix)
            subtitle = 'by {0}, updated {1}'.format(workflow['author'],
                                                    relative_time(
                                                        workflow['updated']))
            self.wf.add_item(title,
                             subtitle,
                             # Pass bundle ID to Packal.org search
                             arg=workflow['bundle'],
                             valid=True,
                             icon=ICON_WFLOW)

        self.wf.send_feedback()
        return 0

    def _workflow_by_bundleid(self, bid):
        for workflow in self.workflows:
            if workflow['bundle'] == bid:
                return workflow
        log.error('Bundle ID not found : {}'.format(self.bundleid))
        raise KeyError('Bundle ID unknown : {}'.format(bid))

    def _split_query(self, query):
        if not query or not DELIMITER in query:
            return None, query
        elif query.endswith(DELIMITER):  # trailing space deleted
            raise GoBack(query.rstrip(DELIMITER).strip())
        return [s.strip() for s in query.split(DELIMITER)]

    def _workflow_status(self, bundleid):
        """Return status of workflow

        STATUS_UNKNOWN = not on Packal
        STATUS_UPDATE_AVAILABLE = update available
        STATUS_UP_TO_DATE = from Packal, up-to-date
        STATUS_SPLITTER = on Packal, but not installed from there

        """
        # bundleid = workflow['bundle']
        packal_workflow = None
        for wf in self.workflows:
            if wf['bundle'] == bundleid:
                packal_workflow = wf
        if not packal_workflow:
            return STATUS_UNKNOWN

        remote_version = packal_workflow['version']

        for wfid in self.installed_workflows:
            if wfid == bundleid:
                local_version = self.installed_workflows.get(wfid)
                if not local_version:
                    return STATUS_SPLITTER
                if local_version == remote_version:
                    return STATUS_UP_TO_DATE
                elif local_version < remote_version:
                    return STATUS_UPDATE_AVAILABLE


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    pk = PackalWorkflow()
    wf.run(pk.run)
