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

from datetime import datetime
from operator import itemgetter
from collections import defaultdict
import re
try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET


from workflow import Workflow, web, ICON_INFO, ICON_WARNING

log = None

DELIMITER = '➣'

MANIFEST_URL = 'https://raw.github.com/packal/repository/master/manifest.xml'
SEARCH_URL = 'http://www.packal.org/search/site/{0}'
ICON_WFLOW = '/Applications/Alfred 2.app/Contents/Resources/workflowicon.icns'


__usage__ = """packal.py [options] <action> [<query>]

Usage:
    packal.py workflows [<query>]
    packal.py update
    packal.py tags [<query>]
    packal.py categories [<query>]
    packal.py versions [<query>]
    packal.py authors [<query>]
"""


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
        workflows.append(d)
    return workflows


def workflow_key(workflow):
    """Return text search key for workflow"""
    # I wish tags were in the manifest :(
    elements = [workflow['name']]
    elements.extend(workflow['tags'])
    elements.extend(workflow['categories'])
    elements.append(workflow['author'])
    return ' '.join(elements)


def main(wf):
    from docopt import docopt
    args = docopt(__usage__, argv=wf.args)
    query = args.get('<query>')

    workflows = wf.cached_data('workflows', get_workflows, max_age=1200)
    workflows.sort(key=itemgetter('updated'), reverse=True)
    log.debug('%d workflows found', len(workflows))

    # search all fields
    if args.get('workflows'):
        if DELIMITER in query:
            section, query = [s.strip() for s in query.split(DELIMITER)]
            section, name = section.split(':')

            if section == 'category':
                workflows = [w for w in workflows if name in w['categories']]

            elif section == 'tag':
                workflows = [w for w in workflows if name in w['tags']]

            elif section == 'author':
                workflows = [w for w in workflows if name == w['author']]

            elif section == 'version':
                workflows = [w for w in workflows if name in w['osx']]

        if query:
            workflows = wf.filter(query, workflows, key=workflow_key,
                                  min_score=30)
            log.debug('%d workflows match query', len(workflows))

        if not workflows:
            wf.add_item('Nothing found', 'Try a different query',
                        valid=False, icon=ICON_WARNING)

        for workflow in workflows:
            subtitle = 'by {0}, updated {1}'.format(workflow['author'],
                                                    relative_time(
                                                        workflow['updated']))
            wf.add_item(workflow['name'],
                        subtitle,
                        # Pass bundle ID to Packal.org search
                        arg=SEARCH_URL.format(workflow['bundle']),
                        valid=True,
                        icon=ICON_WFLOW
                        )

        wf.send_feedback()
        return 0

    # search tags
    elif args.get('tags'):

        tags = defaultdict(int)
        for workflow in workflows:
            for tag in workflow['tags']:
                tags[tag] += 1
        tags = sorted([(v, k) for (k, v) in tags.items()], reverse=True)

        if query:
            tags = wf.filter(query, tags, lambda t: t[1], min_score=30)

        for count, tag in tags:
            wf.add_item(tag, '{} workflows'.format(count),
                        valid=True,
                        arg='tag:{}'.format(tag),
                        icon=ICON_WFLOW)

        wf.send_feedback()
        return 0

    # search categories
    elif args.get('categories'):

        categories = defaultdict(int)
        for workflow in workflows:
            for category in workflow['categories']:
                categories[category] += 1
        categories = sorted([(v, k) for (k, v) in categories.items()],
                            reverse=True)

        if query:
            categories = wf.filter(query, categories, lambda t: t[1],
                                   min_score=30)

        for count, category in categories:
            wf.add_item(category, '{} workflows'.format(count),
                        valid=True,
                        arg='category:{}'.format(category),
                        icon=ICON_WFLOW)

        wf.send_feedback()
        return 0

    # search OS X versions
    elif args.get('versions'):

        versions = defaultdict(int)
        for workflow in workflows:
            for version in workflow['osx']:
                versions[version] += 1
        versions = sorted([(v, k) for (k, v) in versions.items()],
                          reverse=True)

        if query:
            versions = wf.filter(query, versions, lambda t: t[1], min_score=30)

        for count, version in versions:
            wf.add_item(version, '{} workflows'.format(count),
                        valid=True,
                        arg='version:{}'.format(version),
                        icon=ICON_WFLOW)

        wf.send_feedback()
        return 0


if __name__ == '__main__':
    wf = Workflow()
    log = wf.logger
    wf.run(main)
