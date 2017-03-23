#!/usr/bin/python
# -*- coding: utf-8 -*-
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2015 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the licence, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# Authors: Alberto Ruiz <aruiz@redhat.com>
#          Oliver Gutiérrez <ogutierrez@redhat.com>

import os
import sys
import tempfile
import shutil
import unittest
import json

import freeipamock

sys.path.append(os.path.join(os.environ['TOPSRCDIR'], 'admin'))

from fleetcommander import freeipa

# Mocking assignments
freeipa.api = freeipamock.FreeIPAMock
freeipa.errors = freeipamock.FreeIPAErrors


class TestFreeIPA(unittest.TestCase):

    maxDiff = None

    # ipa = FreeIPAConnector()
    #
    # print(ipa.check_user_exists('admin'))
    # print(ipa.check_group_exists('admins'))
    # print(ipa.check_host_exists('client1'))
    # print(ipa.check_hostgroup_exists('ipaservers2'))
    # ipa.save_profile({
    #     'uid': 'MYUID',
    #     'description': 'Hola',
    #     'priority': 100,
    #     'settings': {
    #         'org.freedesktop.NetworkManager': [],
    #         'org.gnome.gsettings': [
    #             {
    #                 'schema': 'org.gnome.desktop.notifications.application',
    #                 'key': '/org/gnome/desktop/notifications/application/abrt-applet/application-id',
    #                 'value': "'abrt-applet.desktop'",
    #                 'signature': 's',
    #             }
    #         ],
    #     },
    #     'users': ['guest', 'pepe', 'admin', ],
    #     'groups': ['admins', 'editors', ],
    #     'hosts': ['client1', ],
    #     'hostgroups': ['ipaservers', ],
    # })
    # print(ipa.get_profile('MYUID'))
    # ipa.del_profile('MYUID')

    # def setUp(self):
    #     self.test_directory = tempfile.mkdtemp(prefix='fc-freeipa-test-')
    #     # Set environment for commands execution
    #     os.environ['FC_TEST_DIRECTORY'] = self.test_directory

    # def tearDown(self):
    #     # Remove test directory
    #     shutil.rmtree(self.test_directory)

    TEST_PROFILE = {
        'uid': 'Test Profile',
        #'name': 'Test Profile',
        'description': 'My test profile',
        'priority': 100,
        'settings': {
            'org.freedesktop.NetworkManager': [],
            'org.gnome.gsettings': [
                {
                    'schema': 'org.gnome.desktop.notifications.application',
                    'key': '/org/gnome/desktop/notifications/application/abrt-applet/application-id',
                    'value': "'abrt-applet.desktop'",
                    'signature': 's',
                }
            ],
        },
        'users': sorted(['guest', 'admin', ]),
        'groups': sorted(['admins', 'editors', ]),
        'hosts': sorted(['client1', ]),
        'hostgroups': sorted(['ipaservers', ]),
    }

    SAVED_PROFILE_DATA = {
        u'cn': (TEST_PROFILE['uid'],),
        u'description': (TEST_PROFILE['description'],),
        u'ipadeskdata': (json.dumps(TEST_PROFILE['settings']),),
    }

    SAVED_PROFILERULE_DATA = {
        'priority': 100,
        'users': ['admin', 'guest'],
        'groups': ['admins', 'editors'],
        'hosts': ['client1'],
        'hostgroups': ['ipaservers'],
    }

    TEST_PROFILE_MOD = {
        'uid': 'Test Profile',
        #'name': 'Test Profile',
        'description': 'Test profile modified',
        'priority': 50,
        'settings': {
            'org.freedesktop.NetworkManager': [],
            'org.gnome.gsettings': [
                {
                    'schema': 'org.gnome.desktop.notifications.application',
                    'key': '/org/gnome/desktop/notifications/application/abrt-applet/application-id',
                    'value': "'abrt-applet.desktop'",
                    'signature': 's',
                }
            ],
        },
        'users': sorted(['admin', ]),
        'groups': sorted(['admins', 'editors', ]),
        'hosts': sorted(['client1', ]),
        'hostgroups': sorted(['ipaservers', ]),
    }

    SAVED_PROFILE_DATA_MOD = {
        u'cn': (TEST_PROFILE_MOD['uid'],),
        u'description': (TEST_PROFILE_MOD['description'],),
        u'ipadeskdata': (json.dumps(TEST_PROFILE_MOD['settings']),),
    }

    SAVED_PROFILERULE_DATA_MOD = {
        'priority': 50,
        'users': ['admin', ],
        'groups': ['admins', 'editors'],
        'hosts': ['client1'],
        'hostgroups': ['ipaservers'],
    }

    def setUp(self):
        self.ipa = freeipa.FreeIPAConnector()
        freeipamock.FreeIPACommand.data = freeipamock.FreeIPAData()

    def test_01_check_user_exists(self):
        # Check existent user
        self.assertTrue(self.ipa.check_user_exists('admin'))
        # Check inexistent user
        self.assertFalse(self.ipa.check_user_exists('fake'))

    def test_02_check_group_exists(self):
        # Check existent group
        self.assertTrue(self.ipa.check_group_exists('admins'))
        # Check inexistent group
        self.assertFalse(self.ipa.check_group_exists('fake'))

    def test_03_check_host_exists(self):
        # Check existent host
        self.assertTrue(self.ipa.check_host_exists('client1'))
        # Check inexistent host
        self.assertFalse(self.ipa.check_host_exists('fake'))

    def test_04_check_hostgroup_exists(self):
        # Check existent hostgroup
        self.assertTrue(self.ipa.check_hostgroup_exists('ipaservers'))
        # Check inexistent hostgroup
        self.assertFalse(self.ipa.check_hostgroup_exists('fake'))

    def test_05_create_profile(self):
        uid = self.TEST_PROFILE['uid']
        self.ipa.create_profile(self.TEST_PROFILE)
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profiles,
            {uid: self.SAVED_PROFILE_DATA})
        # Check profile rule
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profilerules,
            {uid: self.SAVED_PROFILERULE_DATA})
        with self.assertRaises(freeipa.errors.DuplicateEntry):
            self.ipa.create_profile(self.TEST_PROFILE)

    def test_06_check_profile_exists(self):
        uid = self.TEST_PROFILE['uid']
        # Check non existent profile
        self.assertFalse(self.ipa.check_profile_exists(uid))
        # Add profile
        self.ipa.create_profile(self.TEST_PROFILE)
        # Check existent user
        self.assertTrue(self.ipa.check_profile_exists(uid))

    def test_07_update_profile(self):
        uid = self.TEST_PROFILE['uid']
        self.ipa.create_profile(self.TEST_PROFILE)
        # Save a profile with same UID (overwrite)
        self.ipa.update_profile(self.TEST_PROFILE_MOD)
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profiles,
            {uid: self.SAVED_PROFILE_DATA_MOD})
        # Check profile rule
        self.assertEqual(
            freeipamock.FreeIPACommand.data.profilerules,
            {uid: self.SAVED_PROFILERULE_DATA_MOD})

    def test_08_del_profile(self):
        # Save a profile
        self.ipa.create_profile(self.TEST_PROFILE)
        # Delete that profile
        self.ipa.del_profile(self.TEST_PROFILE['uid'])
        self.assertEqual(freeipamock.FreeIPACommand.data.profiles, {})

    def test_09_get_profiles(self):
        profiles = self.ipa.get_profiles()
        self.assertEqual(profiles, [])
        # Add some profile
        result = self.ipa.create_profile(self.TEST_PROFILE)
        profiles = self.ipa.get_profiles()
        self.assertEqual(
            profiles,
            [(self.TEST_PROFILE['uid'], self.TEST_PROFILE['description'])])

    def test_10_get_profile_rule(self):
        self.ipa.create_profile(self.TEST_PROFILE)
        rule = self.ipa.get_profile_rule(self.TEST_PROFILE['uid'])
        self.assertEqual(rule, {
            'memberuser_user': self.TEST_PROFILE['users'],
            'memberuser_group': self.TEST_PROFILE['groups'],
            'memberhost_host': self.TEST_PROFILE['hosts'],
            'memberhost_hostgroup': self.TEST_PROFILE['hostgroups'],
            'ipadeskprofilepriority': (self.TEST_PROFILE['priority'],)
        })

    def test_10_get_profile_applies_from_rule(self):
        self.ipa.create_profile(self.TEST_PROFILE)
        rule = self.ipa.get_profile_rule(self.TEST_PROFILE['uid'])
        applies = self.ipa.get_profile_applies_from_rule(rule)
        self.assertEqual(applies, {
            'users': self.TEST_PROFILE['users'],
            'groups': self.TEST_PROFILE['groups'],
            'hosts': self.TEST_PROFILE['hosts'],
            'hostgroups': self.TEST_PROFILE['hostgroups'],
        })

    def test_11_get_profile(self):
        uid = self.TEST_PROFILE['uid']
        self.ipa.create_profile(self.TEST_PROFILE)
        profile = self.ipa.get_profile(uid)
        self.assertEqual(profile, self.TEST_PROFILE)


if __name__ == '__main__':
    unittest.main()
