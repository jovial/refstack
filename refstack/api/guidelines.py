# Copyright (c) 2016 IBM, Inc.
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

"""Class for retrieving Interop WG guideline information."""

import itertools
from oslo_config import cfg
from oslo_log import log
from operator import itemgetter
import re
import requests
import requests_cache
import json
import os

CONFIG_FILE_NAME = "config.json"

DEFAULT_PLATFORMS_MAP = {
    # TODO: rename targets
    "base": {
        'platform': 'OpenStack Powered Platform',
        'compute': 'OpenStack Powered Compute',
        'object': 'OpenStack Powered Storage',
        'dns': 'OpenStack with DNS',
        'orchestration': 'OpenStack with Orchestration'
    },
    "add-ons": ["dns", "orchestration"]
    # "versions": {
    #     "dns": {
    #         "min": ""
    #         "max": 
    #     }
    # }
}

CONF = cfg.CONF
LOG = log.getLogger(__name__)

# Cached requests will expire after 12 hours.
requests_cache.install_cache(cache_name='github_cache',
                             backend='memory',
                             expire_after=43200)


class Guidelines:
    """This class handles guideline/capability listing and retrieval."""

    def __init__(self,
                 repo_url=None,
                 raw_url=None,
                 additional_capability_urls=None):
        """Initialize class with needed URLs.

        The URL for the guidelines repository is specified with 'repo_url'.
        The URL for where raw files are served is specified with 'raw_url'.
        These values will default to the values specified in the RefStack
        config file.
        """
        self.guideline_sources = list()
        if additional_capability_urls:
            self.additional_urls = additional_capability_urls.split(',')
        else:
            self.additional_urls = \
                CONF.api.additional_capability_urls.split(',')
        [self.guideline_sources.append(url) for url in self.additional_urls]
        if repo_url:
            self.repo_url = repo_url
        else:
            self.repo_url = CONF.api.github_api_capabilities_url
        if self.repo_url and self.repo_url not in self.guideline_sources:
            self.guideline_sources.append(self.repo_url)
        if raw_url:
            self.raw_url = raw_url
        else:
            self.raw_url = CONF.api.github_raw_base_url
        self.config_url = ''.join(
            (self.raw_url.rstrip('/'), '/', CONFIG_FILE_NAME)
        )

    # TODO: call this metadata?
    def _get_config(self):
        try:
            resp = requests.get(self.config_url)
            if resp.status_code == 200:
                return resp.json()
            else:
                LOG.warning('Guidelines repo URL (%s) returned '
                            'non-success HTTP code: %s' %
                            (self.config_url, resp.status_code))
                return json.dumps({})
        except requests.exceptions.RequestException as e:
            LOG.warning('An error occurred trying to get config '
                        'contents through %s: %s' % (self.config_url, e))

    def get_platform_map(self):
        config = self._get_config()
        if not config or "platformMap" not in config:
            LOG.debug("Using default platform map")
            return DEFAULT_PLATFORMS_MAP
        return config["platformMap"]

    def get_guideline_list(self):
        # TODO: the output of this is no longer exposed via rest, so
        # we could add checkums for instance
        """Return a list of a guideline files.

        The repository url specificed in class instantiation is checked
        for a list of JSON guideline files. A list of these is returned.
        """
        capability_files = {}
        capability_list = []
        powered_files = []
        addon_files = []
        for src_url in self.guideline_sources:
            try:
                resp = requests.get(src_url)

                LOG.debug("Response Status: %s / Used Requests Cache: %s" %
                          (resp.status_code,
                           getattr(resp, 'from_cache', False)))
                if resp.status_code == 200:
                    regex = re.compile('([0-9]{4}\.[0-9]{2}|next)\.json')
                    for rfile in resp.json():
                        if rfile["type"] == "file" and \
                                regex.search(rfile["name"]):
                            if 'add-ons' in rfile['path'] and \
                                    rfile[
                                        'name'] not in map(itemgetter('name'),
                                                           addon_files):
                                file_dict = {'name': rfile['name']}
                                addon_files.append(file_dict)
                            elif 'add-ons' not in rfile['path'] and \
                                rfile['name'] not in map(itemgetter('name'),
                                                         powered_files):
                                file_dict = {'name': rfile['name'],
                                             'file': rfile['path']}
                                powered_files.append(file_dict)
                else:
                    LOG.warning('Guidelines repo URL (%s) returned '
                                'non-success HTTP code: %s' %
                                (src_url, resp.status_code))

            except requests.exceptions.RequestException as e:
                LOG.warning('An error occurred trying to get repository '
                            'contents through %s: %s' % (src_url, e))
        for k, v in itertools.groupby(addon_files,
                                      key=lambda x: x['name'].split('.')[0]):
            values = [{'name': x['name'].split('.', 1)[1], 'file': x['name']}
                      for x in list(v)]
            capability_list.append((k, list(values)))
        capability_list.append(('powered', powered_files))
        capability_files = dict((x, y) for x, y in capability_list)
        return capability_files

    def _is_addon(self, gl_file):
        regex = re.compile("[a-z]*\.([0-9]{4}\.[0-9]{2}|next)\.json")
        return regex.search(gl_file)

    def get_guideline_contents(self, category, version):
        """Get contents for a given category and version."""

        if category == "powered":
            # non-addons
            guideline_path = version
        else:
            guideline_path = "add-ons/%s.%s" % (category, version)

        guideline_path = '.'.join((guideline_path, 'json'))

        file_url = ''.join((self.raw_url.rstrip('/'),
                            '/', guideline_path))
        LOG.debug("file_url: %s" % (file_url))
        try:
            response = requests.get(file_url)
            LOG.debug("Response Status: %s / Used Requests Cache: %s" %
                      (response.status_code,
                       getattr(response, 'from_cache', False)))
            LOG.debug("Response body: %s" % str(response.text))
            if response.status_code == 200:
                return response.json()
            else:
                LOG.warning('Raw guideline URL (%s) returned non-success HTTP '
                            'code: %s' % (self.raw_url, response.status_code))

                return None
        except requests.exceptions.RequestException as e:
            LOG.warning('An error occurred trying to get raw capability file '
                        'contents from %s: %s' % (self.raw_url, e))
            return None

    def get_target_capabilities(self, guideline_json, types=None,
                                target='platform'):
        """Get list of capabilities that match the given statuses and target.

        If no list of types in given, then capabilities of all types
        are given. If not target is specified, then all capabilities are given.
        """
        platforms_map = self.get_platform_map()
        components = guideline_json['components']
        if ('metadata' in guideline_json and
                guideline_json['metadata']['schema'] >= '2.0'):
            schema = guideline_json['metadata']['schema']
            if target in platforms_map["add-ons"]:
                targets = ['os_powered_' + target]
            else:
                platform = platforms_map["base"][target]
                comps = []
                if platform in guideline_json['platforms']:
                    comps = \
                        guideline_json['platforms'][platform]['components']
                targets = (obj['name'] for obj in comps)
        else:
            schema = guideline_json['schema']
            targets = set()
            if target != 'platform':
                targets.add(target)
            else:
                targets.update(guideline_json['platform']['required'])
        target_caps = set()
        for component in targets:
            complist = components[component]
            if schema >= '2.0':
                complist = complist['capabilities']
            for status, capabilities in complist.items():
                if types is None or status in types:
                    target_caps.update(capabilities)
        return list(target_caps)

    def _get_version(self, guideline_file):
        # strip the json extension
        name = os.path.splitext(guideline_file)[0]
        if self._is_addon(guideline_file):
            # 0th component is the category e.g dns in dns.2015.07
            return name.split('.', 1)[1]
        return name

    def get_versions(self, gl_type):
        # TODO: use cache if checksums not changed
        LOG.debug("Using gl_type: %s" % gl_type)
        guidelines = self.get_guideline_list()
        versions = set()
        if gl_type not in guidelines:
            return []
        for guideline in guidelines[gl_type]:
            guideline_file = guideline["file"]
            version = self._get_version(guideline_file)
            content = self.get_guideline_contents(category=gl_type, version=version)
            kwargs = {}
            if gl_type != "powered":
                kwargs["target"] = gl_type
            if self._supports_target(content, **kwargs):
                versions.add(version)
        return list(versions)

    def _supports_target(self, guideline_json, **kwargs):
        if self.get_target_capabilities(guideline_json, **kwargs):
            return True
        return False

    def get_test_list(self, guideline_json, capabilities=[],
                      alias=True, show_flagged=True):
        """Generate a test list based on input.

        A test list is formed from the given guideline JSON data and
        list of capabilities. If 'alias' is True, test aliases are
        included in the list. If 'show_flagged' is True, flagged tests are
        included in the list.
        """
        caps = guideline_json['capabilities']
        if ('metadata' in guideline_json and
                guideline_json['metadata']['schema'] >= '2.0'):
            schema = guideline_json['metadata']['schema']
        else:
            schema = guideline_json['schema']
        test_list = []
        for cap, cap_details in caps.items():
            if cap in capabilities:
                if schema == '1.2':
                    for test in cap_details['tests']:
                        if show_flagged:
                            test_list.append(test)
                        elif not show_flagged and \
                                test not in cap_details['flagged']:
                            test_list.append(test)
                else:
                    for test, test_details in cap_details['tests'].items():
                        added = False
                        if test_details.get('flagged'):
                            if show_flagged:
                                test_str = '{}[{}]'.format(
                                    test,
                                    test_details.get('idempotent_id', '')
                                )
                                test_list.append(test_str)
                                added = True
                        else:
                            # Make sure the test UUID is in the test string.
                            test_str = '{}[{}]'.format(
                                test,
                                test_details.get('idempotent_id', '')
                            )
                            test_list.append(test_str)
                            added = True

                        if alias and test_details.get('aliases') and added:
                            for alias in test_details['aliases']:
                                test_str = '{}[{}]'.format(
                                    alias,
                                    test_details.get('idempotent_id', '')
                                )
                                test_list.append(test_str)
        test_list.sort()
        return test_list
