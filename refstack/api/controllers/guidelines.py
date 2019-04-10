#!/usr/bin/env python
# Copyright (c) 2015 Mirantis, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Interop WG guidelines controller."""

import pecan
from pecan import rest

import urlparse

from refstack.api import constants as const
from refstack.api import guidelines
from refstack.api import utils as api_utils

from oslo_log import log
LOG = log.getLogger(__name__)


class TestsController(rest.RestController):
    """v1/guidelines/<version>/tests handler.

    This will allow users to retrieve specific test lists from specific
    guidelines for use with refstack-client.
    """

    @pecan.expose(content_type='text/plain')
    def get(self, version):
        """Get the plain-text test list of the specified guideline version."""
        g = guidelines.Guidelines()
        json = g.get_guideline_contents(version)

        if not json:
            return 'Error getting JSON content for version: ' + version

        if pecan.request.GET.get(const.TYPE):
            types = pecan.request.GET.get(const.TYPE).split(',')
        else:
            types = None

        if pecan.request.GET.get('alias'):
            alias = api_utils.str_to_bool(pecan.request.GET.get('alias'))
        else:
            alias = True

        if pecan.request.GET.get('flag'):
            flag = api_utils.str_to_bool(pecan.request.GET.get('flag'))
        else:
            flag = True

        target = pecan.request.GET.get('target', 'platform')
        try:
            target_caps = g.get_target_capabilities(json, types, target)
            test_list = g.get_test_list(json, target_caps, alias, flag)
        except KeyError:
            return 'Invalid target: ' + target

        return '\n'.join(test_list)


class GuidelinesController(rest.RestController):
    """/v1/guidelines handler.

    This acts as a proxy for retrieving guideline files
    from the openstack/interop Github repository.
    """

    tests = TestsController()

    @pecan.expose('json')
    def get(self, *args, **kwargs):
        """Get a list of all available guidelines."""
        g = guidelines.Guidelines()
        LOG.debug("kwargs: %s" % kwargs)
        LOG.debug("args: %s" % repr(args))
        if 'path' in kwargs:
            return self.get_content(kwargs["path"])
        elif args:
            # pecan will strip the json extension
            path = "/".join(args) + ".json"
            LOG.debug("path: %s" % path)
            return self.get_content(path)
        version_list = g.get_guideline_list()
        if version_list is None:
            pecan.abort(500, 'The server was unable to get a list of '
                             'guidelines from the external source.')
        else:
            return version_list

    def get_content(self, path):
        """Handler for getting contents of specific guideline file."""
        g = guidelines.Guidelines()
        json = g.get_guideline_contents(path)
        if json:
            return json
        else:
            pecan.abort(500, 'The server was unable to get the JSON '
                             'content for the specified guideline file.')


class PlatformMapController(rest.RestController):
    """/v1/platforms handler.

    This acts as a proxy for retrieving the platform map
    from the openstack/interop Github repository.
    """

    @pecan.expose('json')
    def get(self):
        """Handler for getting the platform map."""
        g = guidelines.Guidelines()
        json = g.get_platform_map()
        if json:
            return json
        else:
            pecan.abort(500, 'The server was unable to get the JSON '
                             'content for the specified guideline file.')
