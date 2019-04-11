
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
    def get(self, category, version):
        """Get the plain-text test list of the specified guideline version."""
        # Remove the .json from version if it is there.
        version.replace('.json', '')
        g = guidelines.Guidelines()
        json = g.get_guideline_contents(category=category, version=version)

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

class VersionsController(rest.RestController):

    tests = TestsController()

    @pecan.expose('json')
    def get(self, category):
        """Handler for getting versions of a specific target."""
        g = guidelines.Guidelines()
        json = g.get_versions(category)
        if json:
            return json
        else:
            pecan.abort(404, 'The server was unable to get the JSON '
                             'content for the specified guideline file.')

    @pecan.expose('json')
    def get_one(self, category, version):
        """Handler for getting contents of specific guideline file."""
        LOG.debug("category: %s" % category)
        LOG.debug("version: %s" % version)
        g = guidelines.Guidelines()
        json = g.get_guideline_contents(category=category, version=version)
        if json:
            return json
        else:
            pecan.abort(500, 'The server was unable to get the JSON '
                        'content for the specified guideline file.')


class GuidelinesController(rest.RestController):
    """/v1/guidelines handler.

    This acts as a proxy for retrieving guideline files
    from the openstack/interop Github repository.
    """

    tests = TestsController()

    @pecan.expose('json')
    def get(self):
        """Get a list of all available guidelines."""
        g = guidelines.Guidelines()
        version_list = g.get_guideline_list()
        if version_list is None:
            pecan.abort(500, 'The server was unable to get a list of '
                             'guidelines from the external source.')
        else:
            return version_list

    @pecan.expose('json')
    def get_one(self, file_name):
        """Handler for getting contents of specific guideline file."""
        g = guidelines.Guidelines()
        json = g.get_guideline_contents(file_name)
        if json:
            return json
        else:
            pecan.abort(500, 'The server was unable to get the JSON '

                        'content for the specified guideline file.')

class TargetsController(rest.RestController):
    """/v1/targets handler.

    This acts as a proxy for retrieving the platform map
    from the openstack/interop Github repository.
    """

    versions = VersionsController()

    @pecan.expose('json')
    def get(self, **kwargs):
        """Handler for getting the platform map."""
        g = guidelines.Guidelines()
        # TODO: return a list
        platform_map = g.get_platform_map()
        json = []
        for k, v in platform_map["base"].items():
            value = {
                # TODO: rename to category for consistency
                "id": k,
                "description": v,
                "add-on": k in platform_map["add-ons"]
            }
            json.append(value)
        if "type" in kwargs:
            typ = kwargs["type"]
            if typ == "add-ons":
                json = [x for x in json if x["add-on"]]
            elif typ == "platform":
                json = [x for x in json if not x["add-on"]]
        return json

    @pecan.expose('json')
    def get_one(self, category):
        """Handler for getting contents of specific guideline file."""
        all = self.get()
        result = [x for x in all if x["id"] == category]
        if result:
            return result[0]
        else:
            pecan.abort(404, 'The server was unable to get the JSON '

                        'content for the specified guideline file.')

