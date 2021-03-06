# -*- coding: utf-8 -*-
# Copyright (C) 2018-2019 Greenbone Networks GmbH
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA

# pylint: disable=invalid-name,line-too-long,no-value-for-parameter

""" Unit Test for ospd-openvas """

import io
import logging

from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock

from ospd.vts import Vts
from ospd.protocol import OspRequest

from tests.dummydaemon import DummyDaemon
from tests.helper import assert_called_once

from ospd_openvas.daemon import OSPD_PARAMS, OpenVasVtsFilter
from ospd_openvas.openvas import Openvas

OSPD_PARAMS_OUT = {
    'auto_enable_dependencies': {
        'type': 'boolean',
        'name': 'auto_enable_dependencies',
        'default': 1,
        'mandatory': 1,
        'description': 'Automatically enable the plugins that are depended on',
    },
    'cgi_path': {
        'type': 'string',
        'name': 'cgi_path',
        'default': '/cgi-bin:/scripts',
        'mandatory': 1,
        'description': 'Look for default CGIs in /cgi-bin and /scripts',
    },
    'checks_read_timeout': {
        'type': 'integer',
        'name': 'checks_read_timeout',
        'default': 5,
        'mandatory': 1,
        'description': 'Number  of seconds that the security checks will '
        'wait for when doing a recv()',
    },
    'drop_privileges': {
        'type': 'boolean',
        'name': 'drop_privileges',
        'default': 0,
        'mandatory': 1,
        'description': '',
    },
    'network_scan': {
        'type': 'boolean',
        'name': 'network_scan',
        'default': 0,
        'mandatory': 1,
        'description': '',
    },
    'non_simult_ports': {
        'type': 'string',
        'name': 'non_simult_ports',
        'default': '22',
        'mandatory': 1,
        'description': 'Prevent to make two connections on the same given '
        'ports at the same time.',
    },
    'open_sock_max_attempts': {
        'type': 'integer',
        'name': 'open_sock_max_attempts',
        'default': 5,
        'mandatory': 0,
        'description': 'Number of unsuccessful retries to open the socket '
        'before to set the port as closed.',
    },
    'timeout_retry': {
        'type': 'integer',
        'name': 'timeout_retry',
        'default': 5,
        'mandatory': 0,
        'description': 'Number of retries when a socket connection attempt '
        'timesout.',
    },
    'optimize_test': {
        'type': 'integer',
        'name': 'optimize_test',
        'default': 5,
        'mandatory': 0,
        'description': 'By default, openvas does not trust the remote '
        'host banners.',
    },
    'plugins_timeout': {
        'type': 'integer',
        'name': 'plugins_timeout',
        'default': 5,
        'mandatory': 0,
        'description': 'This is the maximum lifetime, in seconds of a plugin.',
    },
    'report_host_details': {
        'type': 'boolean',
        'name': 'report_host_details',
        'default': 1,
        'mandatory': 1,
        'description': '',
    },
    'safe_checks': {
        'type': 'boolean',
        'name': 'safe_checks',
        'default': 1,
        'mandatory': 1,
        'description': 'Disable the plugins with potential to crash '
        'the remote services',
    },
    'scanner_plugins_timeout': {
        'type': 'integer',
        'name': 'scanner_plugins_timeout',
        'default': 36000,
        'mandatory': 1,
        'description': 'Like plugins_timeout, but for ACT_SCANNER plugins.',
    },
    'time_between_request': {
        'type': 'integer',
        'name': 'time_between_request',
        'default': 0,
        'mandatory': 0,
        'description': 'Allow to set a wait time between two actions '
        '(open, send, close).',
    },
    'unscanned_closed': {
        'type': 'boolean',
        'name': 'unscanned_closed',
        'default': 1,
        'mandatory': 1,
        'description': '',
    },
    'unscanned_closed_udp': {
        'type': 'boolean',
        'name': 'unscanned_closed_udp',
        'default': 1,
        'mandatory': 1,
        'description': '',
    },
    'expand_vhosts': {
        'type': 'boolean',
        'name': 'expand_vhosts',
        'default': 1,
        'mandatory': 0,
        'description': 'Whether to expand the target hosts '
        + 'list of vhosts with values gathered from sources '
        + 'such as reverse-lookup queries and VT checks '
        + 'for SSL/TLS certificates.',
    },
    'test_empty_vhost': {
        'type': 'boolean',
        'name': 'test_empty_vhost',
        'default': 0,
        'mandatory': 0,
        'description': 'If  set  to  yes, the scanner will '
        + 'also test the target by using empty vhost value '
        + 'in addition to the targets associated vhost values.',
    },
}


class TestOspdOpenvas(TestCase):
    @patch('ospd_openvas.daemon.Openvas')
    def test_set_params_from_openvas_settings(self, mock_openvas: Openvas):
        mock_openvas.get_settings.return_value = {
            'non_simult_ports': '22',
            'plugins_folder': '/foo/bar',
        }
        w = DummyDaemon()
        w.set_params_from_openvas_settings()

        self.assertEqual(mock_openvas.get_settings.call_count, 1)
        self.assertEqual(OSPD_PARAMS, OSPD_PARAMS_OUT)
        self.assertEqual(w.scan_only_params.get('plugins_folder'), '/foo/bar')

    @patch('ospd_openvas.daemon.Openvas')
    def test_sudo_available(self, mock_openvas):
        mock_openvas.check_sudo.return_value = True

        w = DummyDaemon()
        w._sudo_available = None  # pylint: disable=protected-access
        w.sudo_available  # pylint: disable=pointless-statement

        self.assertTrue(w.sudo_available)

    def test_load_vts(self,):
        w = DummyDaemon()
        w.load_vts()

        self.assertIsInstance(w.vts, type(Vts()))
        self.assertEqual(len(w.vts), len(w.VTS))

    def test_get_custom_xml(self):
        out = (
            '<custom>'
            '<required_ports>Services/www, 80</required_ports>'
            '<category>3</category>'
            '<excluded_keys>Settings/disable_cgi_scanning</excluded_keys>'
            '<family>Product detection</family>'
            '<filename>mantis_detect.nasl</filename>'
            '<timeout>0</timeout>'
            '</custom>'
        )
        w = DummyDaemon()

        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        res = w.get_custom_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', vt.get('custom')
        )
        self.assertEqual(len(res), len(out))

    def test_get_custom_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        custom = {'a': u"\u0006"}
        w.get_custom_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', custom=custom
        )

        assert_called_once(logging.Logger.warning)

    def test_get_severities_xml(self):
        w = DummyDaemon()

        out = (
            '<severities>'
            '<severity type="cvss_base_v2">'
            'AV:N/AC:L/Au:N/C:N/I:N/A:N'
            '</severity>'
            '</severities>'
        )
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        severities = vt.get('severities')
        res = w.get_severities_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', severities
        )

        self.assertEqual(res, out)

    def test_get_severities_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        sever = {'severity_base_vector': u"\u0006"}
        w.get_severities_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', severities=sever
        )

        assert_called_once(logging.Logger.warning)

    def test_get_params_xml(self):
        w = DummyDaemon()
        out = (
            '<params>'
            '<param type="checkbox" id="2">'
            '<name>Do not randomize the  order  in  which ports are '
            'scanned</name>'
            '<default>no</default>'
            '</param>'
            '<param type="entry" id="1">'
            '<name>Data length :</name>'
            '</param>'
            '</params>'
        )

        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        params = vt.get('vt_params')
        res = w.get_params_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', params)

        self.assertEqual(len(res), len(out))

    def test_get_params_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        params = {
            '1': {
                'id': '1',
                'type': 'entry',
                'default': u'\u0006',
                'name': 'dns-fuzz.timelimit',
                'description': 'Description',
            }
        }
        w.get_params_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', params)

        assert_called_once(logging.Logger.warning)

    def test_get_refs_xml(self):
        w = DummyDaemon()

        out = '<refs><ref type="url" id="http://www.mantisbt.org/"/></refs>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        refs = vt.get('vt_refs')
        res = w.get_refs_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', refs)

        self.assertEqual(res, out)

    def test_get_dependencies_xml(self):
        w = DummyDaemon()

        out = (
            '<dependencies>'
            '<dependency vt_id="1.2.3.4"/><dependency vt_id="4.3.2.1"/>'
            '</dependencies>'
        )
        dep = ['1.2.3.4', '4.3.2.1']
        res = w.get_dependencies_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', dep
        )

        self.assertEqual(res, out)

    def test_get_dependencies_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.error = Mock()

        dep = [u"\u0006"]
        w.get_dependencies_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', vt_dependencies=dep
        )

        assert_called_once(logging.Logger.error)

    def test_get_ctime_xml(self):
        w = DummyDaemon()

        out = '<creation_time>1237458156</creation_time>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        ctime = vt.get('creation_time')
        res = w.get_creation_time_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', ctime
        )

        self.assertEqual(res, out)

    def test_get_ctime_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        ctime = u'\u0006'
        w.get_creation_time_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', vt_creation_time=ctime
        )

        assert_called_once(logging.Logger.warning)

    def test_get_mtime_xml(self):
        w = DummyDaemon()

        out = '<modification_time>1533906565</modification_time>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        mtime = vt.get('modification_time')
        res = w.get_modification_time_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', mtime
        )

        self.assertEqual(res, out)

    def test_get_mtime_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        mtime = u'\u0006'
        w.get_modification_time_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', mtime
        )

        assert_called_once(logging.Logger.warning)

    def test_get_summary_xml(self):
        w = DummyDaemon()

        out = '<summary>some summary</summary>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        summary = vt.get('summary')
        res = w.get_summary_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', summary
        )

        self.assertEqual(res, out)

    def test_get_summary_xml_failed(self):
        w = DummyDaemon()

        summary = u'\u0006'
        logging.Logger.warning = Mock()
        w.get_summary_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', summary)

        assert_called_once(logging.Logger.warning)

    def test_get_impact_xml(self):
        w = DummyDaemon()

        out = '<impact>some impact</impact>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        impact = vt.get('impact')
        res = w.get_impact_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', impact)

        self.assertEqual(res, out)

    def test_get_impact_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        impact = u'\u0006'
        w.get_impact_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', impact)

        assert_called_once(logging.Logger.warning)

    def test_get_insight_xml(self):
        w = DummyDaemon()

        out = '<insight>some insight</insight>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        insight = vt.get('insight')
        res = w.get_insight_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', insight
        )

        self.assertEqual(res, out)

    def test_get_insight_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        insight = u'\u0006'
        w.get_insight_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', insight)

        assert_called_once(logging.Logger.warning)

    def test_get_solution_xml(self):
        w = DummyDaemon()

        out = (
            '<solution type="WillNotFix" method="DebianAPTUpgrade">'
            'some solution'
            '</solution>'
        )
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        solution = vt.get('solution')
        solution_type = vt.get('solution_type')
        solution_method = vt.get('solution_method')

        res = w.get_solution_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061',
            solution,
            solution_type,
            solution_method,
        )

        self.assertEqual(res, out)

    def test_get_solution_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        solution = u'\u0006'
        w.get_solution_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', solution)

        assert_called_once(logging.Logger.warning)

    def test_get_detection_xml(self):
        w = DummyDaemon()

        out = '<detection qod_type="remote_banner"/>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        detection_type = vt.get('qod_type')

        res = w.get_detection_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', qod_type=detection_type
        )

        self.assertEqual(res, out)

    def test_get_detection_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        detection = u'\u0006'
        w.get_detection_vt_as_xml_str('1.3.6.1.4.1.25623.1.0.100061', detection)

        assert_called_once(logging.Logger.warning)

    def test_get_affected_xml(self):
        w = DummyDaemon()
        out = '<affected>some affection</affected>'
        vt = w.VTS['1.3.6.1.4.1.25623.1.0.100061']
        affected = vt.get('affected')

        res = w.get_affected_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', affected=affected
        )

        self.assertEqual(res, out)

    def test_get_affected_xml_failed(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        affected = u"\u0006" + "affected"
        w.get_affected_vt_as_xml_str(
            '1.3.6.1.4.1.25623.1.0.100061', affected=affected
        )

        assert_called_once(logging.Logger.warning)

    def test_build_credentials(self):
        w = DummyDaemon()

        cred_out = [
            '1.3.6.1.4.1.25623.1.0.105058:1:entry:ESXi login name:|||username',
            '1.3.6.1.4.1.25623.1.0.105058:2:password:ESXi login password:|||pass',
            'auth_port_ssh|||22',
            '1.3.6.1.4.1.25623.1.0.103591:1:entry:SSH login name:|||username',
            '1.3.6.1.4.1.25623.1.0.103591:2:password:SSH key passphrase:|||pass',
            '1.3.6.1.4.1.25623.1.0.103591:4:file:SSH private key:|||',
            '1.3.6.1.4.1.25623.1.0.90023:1:entry:SMB login:|||username',
            '1.3.6.1.4.1.25623.1.0.90023:2:password]:SMB password :|||pass',
            '1.3.6.1.4.1.25623.1.0.105076:1:password:SNMP Community:some comunity',
            '1.3.6.1.4.1.25623.1.0.105076:2:entry:SNMPv3 Username:username',
            '1.3.6.1.4.1.25623.1.0.105076:3:password:SNMPv3 Password:pass',
            '1.3.6.1.4.1.25623.1.0.105076:4:radio:SNMPv3 Authentication Algorithm:some auth algo',
            '1.3.6.1.4.1.25623.1.0.105076:5:password:SNMPv3 Privacy Password:privacy pass',
            '1.3.6.1.4.1.25623.1.0.105076:6:radio:SNMPv3 Privacy Algorithm:privacy algo',
        ]
        cred_dict = {
            'ssh': {
                'type': 'ssh',
                'port': '22',
                'username': 'username',
                'password': 'pass',
            },
            'smb': {'type': 'smb', 'username': 'username', 'password': 'pass'},
            'esxi': {
                'type': 'esxi',
                'username': 'username',
                'password': 'pass',
            },
            'snmp': {
                'type': 'snmp',
                'username': 'username',
                'password': 'pass',
                'community': 'some comunity',
                'auth_algorithm': 'some auth algo',
                'privacy_password': 'privacy pass',
                'privacy_algorithm': 'privacy algo',
            },
        }

        ret = w.build_credentials_as_prefs(cred_dict)

        self.assertEqual(len(ret), len(cred_out))
        self.assertIn('auth_port_ssh|||22', cred_out)
        self.assertIn(
            '1.3.6.1.4.1.25623.1.0.90023:1:entry:SMB login:|||username',
            cred_out,
        )

    def test_build_credentials_ssh_up(self):
        w = DummyDaemon()

        cred_out = [
            'auth_port_ssh|||22',
            '1.3.6.1.4.1.25623.1.0.103591:1:entry:SSH login name:|||username',
            '1.3.6.1.4.1.25623.1.0.103591:3:password:SSH password (unsafe!):|||pass',
        ]
        cred_dict = {
            'ssh': {
                'type': 'up',
                'port': '22',
                'username': 'username',
                'password': 'pass',
            }
        }

        ret = w.build_credentials_as_prefs(cred_dict)

        self.assertEqual(ret, cred_out)

    def test_build_alive_test_opt_empty(self):
        w = DummyDaemon()

        target_options_dict = {'alive_test': '0'}

        ret = w.build_alive_test_opt_as_prefs(target_options_dict)

        self.assertEqual(ret, [])

    def test_build_alive_test_opt(self):
        w = DummyDaemon()

        alive_test_out = [
            "1.3.6.1.4.1.25623.1.0.100315:1:checkbox:Do a TCP ping|||no",
            "1.3.6.1.4.1.25623.1.0.100315:2:checkbox:TCP ping tries also TCP-SYN ping|||no",
            "1.3.6.1.4.1.25623.1.0.100315:7:checkbox:TCP ping tries only TCP-SYN ping|||no",
            "1.3.6.1.4.1.25623.1.0.100315:3:checkbox:Do an ICMP ping|||yes",
            "1.3.6.1.4.1.25623.1.0.100315:4:checkbox:Use ARP|||no",
            "1.3.6.1.4.1.25623.1.0.100315:5:checkbox:Mark unrechable Hosts as dead (not scanning)|||yes",
        ]
        target_options_dict = {'alive_test': '2'}

        ret = w.build_alive_test_opt_as_prefs(target_options_dict)

        self.assertEqual(ret, alive_test_out)

    def test_build_alive_test_opt_fail_1(self):
        w = DummyDaemon()
        logging.Logger.debug = Mock()

        target_options_dict = {'alive_test': 'a'}

        target_options = w.build_alive_test_opt_as_prefs(target_options_dict)

        assert_called_once(logging.Logger.debug)
        self.assertEqual(len(target_options), 0)

    def test_process_vts(self):
        w = DummyDaemon()

        vts = {
            '1.3.6.1.4.1.25623.1.0.100061': {'1': 'new value'},
            'vt_groups': ['family=debian', 'family=general'],
        }
        vt_out = (
            ['1.3.6.1.4.1.25623.1.0.100061'],
            {'1.3.6.1.4.1.25623.1.0.100061:1:entry:Data length :': 'new value'},
        )

        w.load_vts()
        w.temp_vts = w.vts

        ret = w.process_vts(vts)

        self.assertEqual(ret, vt_out)

    def test_process_vts_bad_param_id(self):
        w = DummyDaemon()

        vts = {
            '1.3.6.1.4.1.25623.1.0.100061': {'3': 'new value'},
            'vt_groups': ['family=debian', 'family=general'],
        }

        w.load_vts()
        w.temp_vts = w.vts

        ret = w.process_vts(vts)

        self.assertFalse(ret[1])

    def test_process_vts_not_found(self):
        w = DummyDaemon()
        logging.Logger.warning = Mock()

        vts = {
            '1.3.6.1.4.1.25623.1.0.100065': {'3': 'new value'},
            'vt_groups': ['family=debian', 'family=general'],
        }

        w.load_vts()
        w.temp_vts = w.vts

        w.process_vts(vts)

        assert_called_once(logging.Logger.warning)

    # def test_get_openvas_timestamp_scan_host_end(self):
    #     w = DummyDaemon()

    #     mock_db.get_host_scan_scan_end_time.return_value = '12345'

    #     target_list = w.create_xml_target()
    #     targets = w.process_targets_element(target_list)

    #     w.create_scan('123-456', targets, None, [])
    #     w.get_openvas_timestamp_scan_host('123-456', '192.168.0.1')

    #     for result in w.scan_collection.results_iterator('123-456', False):
    #         self.assertEqual(result.get('value'), '12345')

    # def test_get_openvas_timestamp_scan_host_start(self):
    #     w = DummyDaemon()

    #     mock_db.get_host_scan_scan_end_time.return_value = None
    #     mock_db.get_host_scan_scan_end_time.return_value = '54321'

    #     target_list = w.create_xml_target()
    #     targets = w.process_targets_element(target_list)

    #     w.create_scan('123-456', targets, None, [])
    #     w.get_openvas_timestamp_scan_host('123-456', '192.168.0.1')

    #     for result in w.scan_collection.results_iterator('123-456', False):
    #         self.assertEqual(result.get('value'), '54321')

    def test_feed_is_healthy_true(self):
        w = DummyDaemon()

        w.nvti.get_nvt_count.return_value = 2
        w.nvti.get_nvt_files_count.return_value = 2
        w.vts = ["a", "b"]

        ret = w.feed_is_healthy()
        self.assertTrue(ret)

    def test_feed_is_healthy_false(self):
        w = DummyDaemon()

        w.nvti.get_nvt_count.return_value = 1
        w.nvti.get_nvt_files_count.return_value = 2

        w.vts = ["a", "b"]

        ret = w.feed_is_healthy()

        self.assertFalse(ret)

        w.nvti.get_nvt_count.return_value = 2
        w.nvti.get_nvt_files_count.return_value = 1

        ret = w.feed_is_healthy()

        self.assertFalse(ret)

        w.nvti.get_nvt_count.return_value = 2
        w.nvti.get_nvt_files_count.return_value = 2

        w.vts = ["a"]

        ret = w.feed_is_healthy()

        self.assertFalse(ret)

    @patch('ospd_openvas.daemon.Path.exists')
    @patch('ospd_openvas.daemon.OSPDopenvas.set_params_from_openvas_settings')
    def test_feed_is_outdated_none(
        self, mock_set_params: MagicMock, mock_path_exists: MagicMock
    ):
        w = DummyDaemon()

        w.scan_only_params['plugins_folder'] = '/foo/bar'

        # Return None
        mock_path_exists.return_value = False

        ret = w.feed_is_outdated('1234')
        self.assertIsNone(ret)

        self.assertEqual(mock_set_params.call_count, 1)
        self.assertEqual(mock_path_exists.call_count, 1)

    @patch('ospd_openvas.daemon.Path.exists')
    @patch('ospd_openvas.daemon.Path.open')
    def test_feed_is_outdated_true(
        self, mock_path_open: MagicMock, mock_path_exists: MagicMock,
    ):
        read_data = 'PLUGIN_SET = "1235";'

        mock_path_exists.return_value = True
        mock_read = MagicMock(name='Path open context manager')
        mock_read.__enter__ = MagicMock(return_value=io.StringIO(read_data))
        mock_path_open.return_value = mock_read

        w = DummyDaemon()

        # Return True
        w.scan_only_params['plugins_folder'] = '/foo/bar'

        ret = w.feed_is_outdated('1234')
        self.assertTrue(ret)

        self.assertEqual(mock_path_exists.call_count, 1)
        self.assertEqual(mock_path_open.call_count, 1)

    @patch('ospd_openvas.daemon.Path.exists')
    @patch('ospd_openvas.daemon.Path.open')
    def test_feed_is_outdated_false(
        self, mock_path_open: MagicMock, mock_path_exists: MagicMock,
    ):
        mock_path_exists.return_value = True

        read_data = 'PLUGIN_SET = "1234"'
        mock_path_exists.return_value = True
        mock_read = MagicMock(name='Path open context manager')
        mock_read.__enter__ = MagicMock(return_value=io.StringIO(read_data))
        mock_path_open.return_value = mock_read

        w = DummyDaemon()
        w.scan_only_params['plugins_folder'] = '/foo/bar'

        ret = w.feed_is_outdated('1234')
        self.assertFalse(ret)

        self.assertEqual(mock_path_exists.call_count, 1)
        self.assertEqual(mock_path_open.call_count, 1)

    @patch('ospd_openvas.daemon.ScanDB')
    @patch('ospd_openvas.daemon.OSPDaemon.add_scan_log')
    def test_get_openvas_result(self, mock_add_scan_log, MockDBClass):
        w = DummyDaemon()
        mock_db = MockDBClass.return_value

        results = ["LOG||| |||general/Host_Details||| |||Host dead", None]
        mock_db.get_result.side_effect = results
        mock_add_scan_log.return_value = None

        w.load_vts()
        w.report_openvas_results(mock_db, '123-456', 'localhost')

        mock_add_scan_log.assert_called_with(
            '123-456',
            host='localhost',
            hostname='',
            name='',
            port='general/Host_Details',
            qod='',
            test_id='',
            value='Host dead',
        )

    @patch('ospd_openvas.daemon.ScanDB')
    @patch('ospd_openvas.daemon.OSPDaemon.add_scan_log')
    def test_get_openvas_result_escaped(self, mock_ospd, MockDBClass):
        w = DummyDaemon()
        mock_db = MockDBClass.return_value

        results = [
            "LOG||| |||general/Host_Details|||1.3.6.1.4.1.25623.1.0.100061|||Alive",
            None,
        ]
        mock_db.get_result.side_effect = results
        mock_ospd.return_value = None

        w.nvti.QOD_TYPES.__getitem__.return_value = ''

        w.load_vts()
        w.report_openvas_results(mock_db, '123-456', 'localhost')

        mock_ospd.assert_called_with(
            '123-456',
            host='localhost',
            hostname='',
            name='Mantis Detection &amp; foo',
            port='general/Host_Details',
            qod='',
            test_id='1.3.6.1.4.1.25623.1.0.100061',
            value='Alive',
        )

    @patch('ospd_openvas.daemon.OSPDaemon.set_scan_host_progress')
    def test_update_progress(self, mock_set_scan_host_progress):
        w = DummyDaemon()

        mock_set_scan_host_progress.return_value = None

        msg = '0/-1'
        target_element = w.create_xml_target()
        targets = OspRequest.process_target_element(target_element)

        w.create_scan('123-456', targets, None, [])
        w.update_progress('123-456', 'localhost', msg)

        mock_set_scan_host_progress.assert_called_with(
            '123-456', 'localhost', 100
        )


class TestFilters(TestCase):
    def test_format_vt_modification_time(self):
        ovformat = OpenVasVtsFilter()
        td = '1517443741'
        formatted = ovformat.format_vt_modification_time(td)
        self.assertEqual(formatted, "20180201000901")
