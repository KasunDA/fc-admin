#!/usr/bin/python
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
# Author: Alberto Ruiz <aruiz@redhat.com>

import os
import sys
import json
import unittest
import shutil
import urllib
import tempfile
import requests
import socket
import time

class MockResponse:
  pass

class MockRequests:
  DEFAULT_CONTENT = "SOMECONTENT"
  DEFAULT_STATUS  = 200
  exceptions = requests.exceptions
  def __init__(self):
    self.queue = []
    self.raise_error = False
    self.set_default_values()

  def get(self, url):
    if self.raise_error:
      raise requests.exceptions.ConnectionError('Connection failed!')
    self.queue.append(url)
    ret = MockRequests()
    ret.content = self.content
    ret.status_code = self.status_code
    return ret

  def pop(self):
    return self.queue.pop()

  def set_default_values(self):
    self.content = self.DEFAULT_CONTENT
    self.status_code = self.DEFAULT_STATUS
    self.raise_error = False

  def raise_error_on_get(self):
    self.raise_error = True

class MockVncWebSocket:
  def __init__(self, **kwargs):
    self.started = False
    self.args = kwargs
  def start(self):
    self.started = True
  def stop(self):
    self.started = False

PYTHONPATH = os.path.join(os.environ['TOPSRCDIR'], 'admin')
sys.path.append(PYTHONPATH)
import fleet_commander_admin

# assigned mocked objects
fleet_commander_admin.requests = MockRequests()
fleet_commander_admin.VNC_WSOCKET = MockVncWebSocket()

class TestAdmin(unittest.TestCase):
  cookie = "/tmp/fleet-commander-start"
  args = {
      'host': 'localhost',
      'port': 8777,
      'profiles_dir': tempfile.mkdtemp(),
      'data_dir': PYTHONPATH,
  }

  @classmethod
  def setUpClass(cls):
    fleet_commander_admin.app.custom_args = cls.args
    fleet_commander_admin.app.config['TESTING'] = True
    cls.app = fleet_commander_admin.app.test_client()

  @classmethod
  def tearDownClass(cls):
    shutil.rmtree(cls.args['profiles_dir'])

  def setUp(self):
    shutil.rmtree(self.args['profiles_dir'])
    self.args['profiles_dir'] = tempfile.mkdtemp()
    fleet_commander_admin.requests.set_default_values()

  def get_data_from_file(self, path):
    return open(path).read()

  def test_00_profiles(self):
    ret = self.app.get("/profiles/")

    INDEX_FILE = os.path.join (self.args['profiles_dir'], 'index.json')

    self.assertEqual(ret.status_code, 200)
    self.assertTrue(os.path.exists(INDEX_FILE),
        msg='index file was not created')
    self.assertEqual(ret.data, self.get_data_from_file(INDEX_FILE),
        msg='index content was not correct')

  def test_01_attempt_save_unselected_profile(self):
    profile_id = '0123456789'
    profile_data = urllib.urlencode(dict(name='myprofile', description='mydesc', settings={}, groups='', users=''))
    ret = self.app.post('/profile/save/' + profile_id , data=profile_data, content_type='application/x-www-form-urlencode')

    PROFILE = os.path.join (self.args['profiles_dir'], profile_id + '.json')
    self.assertFalse(os.path.exists(PROFILE), msg='profile file was not created')
    self.assertEqual (ret.status_code, 403)
    self.assertEqual (json.dumps(json.loads(ret.data)), json.dumps({"status": "nonexistinguid"}))

  def test_02_session_start_stop(self):
    # Start session
    host = 'somehost'
    ret = self.app.post('/session/start', data='host='+host, content_type='application/x-www-form-urlencoded')

    self.assertTrue (fleet_commander_admin.VNC_WSOCKET.started)
    self.assertEqual (fleet_commander_admin.VNC_WSOCKET.target_host, host)
    self.assertEqual (fleet_commander_admin.VNC_WSOCKET.target_port, 5935)
    self.assertEqual (ret.data, MockRequests.DEFAULT_CONTENT)
    self.assertEqual (ret.status_code, MockRequests.DEFAULT_STATUS)
    self.assertEqual (fleet_commander_admin.requests.pop(), "http://%s:8182/session/start" % host)

    ret = self.app.post('/session/stop', data='host='+host, content_type='application/x-www-form-urlencoded')
    self.assertEqual(fleet_commander_admin.requests.pop(), "http://%s:8182/session/stop" % host)
    self.assertEqual(ret.status_code, 200)
    self.assertEqual(ret.data, MockRequests.DEFAULT_CONTENT)

  def test_03_stop_start_failed_connection(self):
    fleet_commander_admin.requests.raise_error_on_get()

    host = 'somehost'
    rets = [self.app.post('/session/start', data='host='+host, content_type='application/x-www-form-urlencoded'),
            self.app.post('/session/stop', data='host='+host, content_type='application/x-www-form-urlencoded')]

    for ret in rets:
      self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({'status': 'could not connect to host'}))
      self.assertEqual(ret.status_code, 403)

  def test_04_change_select_and_deploy(self):
    host = 'somehost'
    self.app.post('/session/start', data='host='+host, content_type='application/x-www-form-urlencoded')
    fleet_commander_admin.requests.pop()

    change1 = {'key':'/foo/bar', 'schema':'foo', 'value':True, 'signature':'b'}
    ret = self.app.post('/submit_change/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
    self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
    self.assertEqual(ret.status_code, 200)

    change2 = {'key':'/foo/baz', 'schema':'foo', 'value':True, 'signature':'b'}
    ret = self.app.post('/submit_change/org.gnome.gsettings', data=json.dumps(change2), content_type='application/json')
    self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
    self.assertEqual(ret.status_code, 200)

    #Check all changes
    ret = self.app.get("/session/changes")
    self.assertEqual(ret.status_code, 200)
    self.assertEqual(json.dumps(json.loads(ret.data)),
                     json.dumps([[change1['key'], change1['value']],[change2['key'], change2['value']]]))

    #Select changes for the profile and get UUID to save it
    ret = self.app.post('/session/select', data=json.dumps({'sel': [1]}), content_type='application/json')
    self.assertEqual(ret.status_code, 200)

    payload = json.loads(ret.data)
    self.assertTrue(isinstance(payload, dict))
    self.assertTrue(payload.has_key('uuid'))
    self.assertTrue(payload.has_key('status'))
    self.assertEqual(payload['status'], 'ok')

    #Save the profile with the selected changes
    uuid = payload['uuid']
    #FIXME: rename this method to profiles/save
    profile_obj  = {'profile-name': 'myprofile','profile-desc':'mydesc','groups':'', 'users':''}
    profile_data = urllib.urlencode(profile_obj)
    ret = self.app.post("/profile/save/"+uuid, content_type='application/x-www-form-urlencoded', data=profile_data)
    self.assertEqual(ret.status_code, 200)
    self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps({"status":"ok"}))

    #Get index
    ret = self.app.get("/profiles/")
    self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([{'url': uuid, 'displayName': profile_obj['profile-name']}]))

    #Get profile
    ret = self.app.get("/profiles/"+uuid)
    self.assertEqual(ret.status_code, 200)
    profile = json.loads(ret.data)
    self.assertEqual(profile['uid'], uuid)
    self.assertEqual(profile['description'], profile_obj['profile-desc'])
    self.assertEqual(profile['name'], profile_obj['profile-name'])
    self.assertEqual(json.dumps(profile['settings']['org.gnome.gsettings'][0]), json.dumps(change2))

    self.app.post('/session/stop', data='host='+host, content_type='application/x-www-form-urlencoded')
    fleet_commander_admin.requests.pop()

  def test_05_change_merge_several_changes(self):
    host = 'somehost'
    self.app.post('/session/start', data='host='+host, content_type='application/x-www-form-urlencoded')
    fleet_commander_admin.requests.pop()

    change1 = {'key':'/foo/bar', 'schema':'foo', 'value':"first", 'signature':'s'}
    ret = self.app.post('/submit_change/org.gnome.gsettings', data=json.dumps(change1), content_type='application/json')
    self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
    self.assertEqual(ret.status_code, 200)

    change2 = {'key':'/foo/bar', 'schema':'foo', 'value':'second', 'signature':'s'}
    ret = self.app.post('/submit_change/org.gnome.gsettings', data=json.dumps(change2), content_type='application/json')
    self.assertEqual(json.dumps({"status": "ok"}), json.dumps(json.loads(ret.data)))
    self.assertEqual(ret.status_code, 200)

    ret = self.app.get('/session/changes')
    self.assertEqual(ret.status_code, 200)
    self.assertEqual(json.dumps(json.loads(ret.data)), json.dumps([[change2['key'], change2['value']],]))

    self.app.post('/session/stop', data='host='+host, content_type='application/x-www-form-urlencoded')
    fleet_commander_admin.requests.pop()


class TestVncWebsocketManager(unittest.TestCase):
  cookie = "/tmp/fcmdr.test.websockify"
  @classmethod
  def setUpClass(cls):
    if os.path.exists(cls.cookie):
      os.remove(cls.cookie)

  @classmethod
  def tearDownClass(cls):
    if os.path.exists(cls.cookie):
      os.remove(cls.cookie)

  def test_00_start_stop(self):
    args = dict(listen_host='listen', listen_port=9999,
                target_host='target', target_port=8888)
    vnc = fleet_commander_admin.VncWebsocketManager(**args)
    vnc.start()
    time.sleep(0.05) #Give enough time for the script to write the file
    self.assertTrue(os.path.exists(self.cookie))
    self.assertTrue(open(self.cookie).read(),
                    "%s:%s %s:%s" % (args['listen_host'], args['listen_port'],
                                     args['target_host'], args['target_port']))
    vnc.stop()

if __name__ == '__main__':
  unittest.main()
