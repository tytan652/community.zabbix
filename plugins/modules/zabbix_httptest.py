#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: zabbix_httptest
short_description: Create/delete Zabbix httptests aka Web Scenarios
description:
   - Create httptests if they do not exist.
   - Delete existing httptests if they exist.
author:
    - "Trystan Mata (@tytan652)"
requirements:
    - "python >= 2.6"

options:
    state:
        description:
            - Create or delete httptest.
        required: false
        type: str
        default: "present"
        choices: [ "present", "absent" ]
    name:
        description:
            - Name of httptest to create or delete.
        required: true
        type: str
    host_name:
        description:
            - Name of host to add httptest to.
            - Required when I(template_name) is not used.
            - Mutually exclusive with I(template_name).
        required: false
        type: str
    template_name:
        description:
            - Name of template to add httptest to.
            - Required when I(host_name) is not used.
            - Mutually exclusive with I(host_name).
        required: false
        type: str
    params:
        description:
            - Parameters to create/update httptest with.
            - Required if state is "present".
            - Parameters as defined at https://www.zabbix.com/documentation/current/en/manual/api/reference/httptest/object
            - Additionally supported parameters are below.
        required: false
        type: dict
        suboptions:
            status:
                description:
                    - Status of the httptest.
                required: false
                type: str
                choices: [ "enabled", "disabled" ]
            enabled:
                description:
                    - Status of the httptest.
                    - Overrides "status" in API docs.
                required: false
                type: bool
            new_name:
                description:
                    - New name for httptest
                required: false
                type: str

extends_documentation_fragment:
- community.zabbix.zabbix
'''

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.community.zabbix.plugins.module_utils.base import ZabbixBase
import ansible_collections.community.zabbix.plugins.module_utils.helpers as zabbix_utils

class Httptest(ZabbixBase):

    def get_hosts_templates(self, host_name, template_name):
        if host_name is not None:
            try:
                return self._zapi.host.get({"filter": {"host": host_name}})
            except Exception as e:
                self._module.fail_json(msg="Failed to get host: %s" % e)
        else:
            try:
                return self._zapi.template.get({"filter": {"host": template_name}})
            except Exception as e:
                self._module.fail_json(msg="Failed to get template: %s" % e)

    def get_httptests(self, httptest_name, host_name, template_name):
        if host_name is not None:
            host = host_name
        else:
            host = template_name
        httptests = []
        try:
            httptests = self._zapi.httptest.get({'filter': {'name': httptest_name, 'host': host}})
        except Exception as e:
            self._module.fail_json(msg="Failed to get httptests: %s" & e)
        return httptests

    def sanitize_params(self, name, params):
        params['name'] = name
        if 'enabled' in params:
            if params['enabled']:
                params['status'] = 'enabled'
            else:
                params['status'] = 'disabled'
            params.pop("enabled")
        if 'status' in params:
            status = params['status']
            if status == 'enabled':
                params['status'] = 0
            elif status == 'disabled':
                params['status'] = 1
            else:
                self._module.fail_json(msg="Status must be 'enabled' or 'disabled', got %s" % status)

    def add_httptest(self, params):
        if self._module.check_mode:
            self._module.exit_json(changed=True)
        try:
            results = self._zapi.httptest.create(params)
        except Exception as e:
            self._module.fail_json(msg="Failed to create httptest: %s" % e)
        return results

    def update_httptest(self, params):
        if self._module.check_mode:
            self._module.exit_json(changed=True)
        try:
            results = self._zapi.httptest.update(params)
        except Exception as e:
            self._module.fail_json(msg="Failed to update httptest: %s" % e)
        return results

    def check_httptest_changed(self, old_httptest):
        try:
            new_httptest = self._zapi.httptest.get({'httptestid': "%s" % old_httptest['httptestid']})[0]
        except Exception as e:
            self._module.fail_json(msg="Failed to get httptest: %s" % e)
        return old_httptest != new_httptest

    def delete_httptests(self, httptest_ids):
        if self._module.check_mode:
            self._module.exit_json(changed=True)
        try:
            results = self._zapi.httptest.delete(httptest_ids)
        except Exception as e:
            self._module.fail_json(msg="Failed to delete httptests: %s" % e)
        return results


def main():
    argument_spec = zabbix_utils.zabbix_common_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        host_name=dict(type='str', required=False),
        template_name=dict(type='str', required=False),
        params=dict(type='dict', required=False),
        state=dict(type='str', default="present", choices=['present', 'absent']),
    ))
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[
            ['host_name', 'template_name']
        ],
        mutually_exclusive=[
            ['host_name', 'template_name']
        ],
        required_if=[
            ['state', 'present', ['params']]
        ],
        supports_check_mode=True
    )

    name = module.params['name']
    host_name = module.params['host_name']
    template_name = module.params['template_name']
    params = module.params['params']
    state = module.params['state']

    httptest = Httptest(module)

    if state == "absent":
        httptests = httptest.get_httptests(name, host_name, template_name)
        if len(httptests) == 0:
            module.exit_json(changed=False, result="No httptest to delete.")
        else:
            delete_ids = []
            for h in httptests:
                delete_ids.append(h['httptestid'])
            results = httptest.delete_httptests(delete_ids)

    elif state == "present":
        httptest.sanitize_params(name, params)
        httptests = httptest.get_httptests(name, host_name, template_name)
        if 'new_name' in params:
            new_name_httptest = httptest.get_httptests(params['new_name'], host_name, template_name)
            if len(new_name_httptest) > 0:
                module.exit_json(changed=False, results=[{'httptestids': [new_name_httptest][0]['httptestid']}])
        results = []
        if len(httptests) == 0:
            if 'new_name' in params:
                module.fail_json('Cannot rename httptest: %s is not found' % name)
            hosts_templates = httptest.get_hosts_templates(host_name, template_name)
            for hosts_template in hosts_templates:
                if 'hostid' in hosts_template:
                    params['hostid'] = hosts_template['hostid']
                elif 'templateid' in hosts_template:
                    params['hostid'] = hosts_template['templateid']
                else:
                    module.fail_json(msg="host/template did not return id")
                results.append(httptest.add_httptest(params))
            module.exit_json(changed=True, result=results)
        else:
            changed = False
            for h in httptests:
                params['httptestid'] = h['httptestid']
                if 'new_name' in params:
                    params['name'] = params['new_name']
                    params.pop("new_name")
                results.append(httptest.update_httptest(params))
                changed_test = httptest.check_httptest_changed(h)
                if changed_test:
                    changed = True
            module.exit_json(changed=changed, result=results)


if __name__ == '__main__':
    main()
