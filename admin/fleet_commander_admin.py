#!/usr/bin/python
# vi:ts=2 sw=2 sts=2

# Copyright (C) 2014 Red Hat, Inc.
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
#

import os
import json
import requests
import uuid
import logging
import sys
import subprocess

from argparse import ArgumentParser

#compat between Pyhon 2 and 3
try:
  from configparser import ConfigParser, ParsingError
except ImportError:
  from ConfigParser import ConfigParser, ParsingError

from flask import Flask, request, send_from_directory, render_template, jsonify

class VncWebsocketManager(object):
  _COMMAND_TEMPLATE = "websockify %s:%d %s:%d"

  def __init__(self, **kwargs):
    ''' Construction arguments:
      listen_host: host to listen for WS connections
      listen_port: port to listen for WS connections
      target_host: native socket host connection
      target_port: native socket port connection
    '''
    self.listen_host = kwargs.get('listen_host', 'localhost')
    self.listen_port = kwargs.get('listen_port', 8989)
    self.target_host = kwargs.get('target_host', 'localhost')
    self.target_port = kwargs.get('target_port', 5900)
    self.websockify = None
    self.DNULL = open('/dev/null', 'w')

  def start(self):
    if self.websockify:
      return

    command = self._COMMAND_TEMPLATE % (self.listen_host, self.listen_port,
                                        self.target_host, self.target_port)

    self.websockify = subprocess.Popen(command, shell=True,
                                       stdin=self.DNULL, stdout=self.DNULL, stderr=self.DNULL)

  def stop(self):
    if self.websockify:
      self.websockify.kill()
      self.websockify = None

class GoaCollector(object):

  def __init__(self):
    self.json = {}

  def handle_change(self, request):
    self.json = dict(request.json)

  def get_settings(self):
    return self.json


class GSettingsCollector(object):

  def __init__(self):
    self.changes = {}
    self.selection = []

  def remember_selected(self, selected_indices):
    self.selection = []
    sorted_keys = sorted(self.changes.keys())
    for index in selected_indices:
      if index < len(sorted_keys):
        key = sorted_keys[index]
        change = self.changes[key]
        self.selection.append(change)

  def handle_change(self, request):
    self.changes[request.json['key']] = request.json

  def dump_changes(self):
    data = []
    for key, change in sorted(self.changes.items()):
      data.append([key, change['value']])
    return json.dumps(data)

  def get_settings(self):
    return self.selection

##############################################################
app = Flask(__name__)
VNC_WSOCKET = VncWebsocketManager()
deploys = {}
collectors_by_name = {}
global_config = {}

@app.route("/profiles/", methods=["GET"])
def profile_index():
  check_for_profile_index()
  return send_from_directory(app.custom_args['profiles_dir'], "index.json")

@app.route("/profiles/<path:profile_id>", methods=["GET"])
def profiles(profile_id):
  return send_from_directory(app.custom_args['profiles_dir'], profile_id + '.json')

#FIXME: Rename this to profiles
#FIXME: Use JSON instead of urlencoding
@app.route("/profiles/save/<id>", methods=["POST"])
def profile_save(id):
  def write_and_close (path, load):
    f = open(path, 'w+')
    f.write(load)
    f.close()

  if id not in deploys:
    return '{"status": "nonexistinguid"}', 403

  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], 'index.json')
  PROFILE_FILE = os.path.join(app.custom_args['profiles_dir'], id+'.json')

  form = dict(request.form)

  profile = {}
  settings = {}
  groups = []
  users = []

  for name, collector in deploys[id].items():
    settings[name] = collector.get_settings()

  groups = [g.strip() for g in form['groups'][0].split(",")]
  users  = [u.strip() for u in form['users'][0].split(",")]
  groups = filter(None, groups)
  users  = filter(None, users)

  profile["uid"] = id
  profile["name"] = form["profile-name"][0]
  profile["description"] = form["profile-desc"][0]
  profile["settings"] = settings
  profile["applies-to"] = {"users": users, "groups": groups}
  profile["etag"] = "placeholder"

  check_for_profile_index()
  index = json.loads(open(INDEX_FILE).read())
  index.append({"url": id, "displayName": form["profile-name"][0]})
  del deploys[id]

  write_and_close(PROFILE_FILE, json.dumps(profile))
  write_and_close(INDEX_FILE, json.dumps(index))

  return '{"status": "ok"}'

@app.route("/profiles/add", methods=["GET"])
def new_profile():
  return render_template('profile.add.html')

@app.route("/profiles/delete/<uid>", methods=["GET"])
def profile_delete(uid):
  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], 'index.json')
  PROFILE_FILE = os.path.join(app.custom_args['profiles_dir'], uid+'.json')

  try:
    os.remove(PROFILE_FILE)
  except:
    pass

  index = json.loads(open(INDEX_FILE).read())
  for profile in index:
    if (profile["url"] == uid):
      index.remove(profile)

  open(INDEX_FILE, 'w+').write(json.dumps(index))
  return '{"status": "ok"}'

#FIXME: Rename this to profiles
@app.route("/profiles/discard/<id>", methods=["GET"])
def profile_discard(id):
  if id in deploys:
    del deploys[id]
  return '{"status": "ok"}'

#Add a configuration change to a session
@app.route("/changes/submit/<name>", methods=["POST"])
def submit_change(name):
  if name in collectors_by_name:
    collectors_by_name[name].handle_change(request)
    return '{"status": "ok"}'
  else:
    return '{"status": "namespace %s not supported or session not started"}' % name, 403

#Static files
@app.route("/js/<path:js>", methods=["GET"])
def js_files(js):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "js"), js)

@app.route("/css/<path:css>", methods=["GET"])
def css_files(css):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "css"), css)

@app.route("/img/<path:img>", methods=["GET"])
def img_files(img):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "img"), img)

@app.route("/fonts/<path:font>", methods=["GET"])
def font_files(font):
  return send_from_directory(os.path.join(app.custom_args['data_dir'], "fonts"), font)

#View methods
@app.route("/", methods=["GET"])
def index():
  return render_template('index.html')

@app.route("/deploy/<uid>", methods=["GET"])
def deploy(uid):
  return render_template('deploy.html')

#profile builder methods
@app.route("/changes", methods=["GET"])
def session_changes():
  #FIXME: Add GOA changes summary
  #FIXME: return empty json list and 403 if there's no session
  collector = collectors_by_name['org.gnome.gsettings']
  return collector.dump_changes()

@app.route("/session/start", methods=["POST"])
def session_start():
  #FIXME: Prevent starting two sessions
  #FIXME: Use JSON instead of url encoding
  global VNC_WSOCKET
  data = dict(request.form)
  req = None

  if 'host' not in data:
    return '{"status": "no host was specified in POST request"}', 403

  try:
    req = requests.get("http://%s:8182/session/start" % data['host'][0])
  except requests.exceptions.ConnectionError:
    return '{"status": "could not connect to host"}', 403

  VNC_WSOCKET.stop()
  VNC_WSOCKET.target_host = data['host'][0]
  VNC_WSOCKET.target_port = 5935
  VNC_WSOCKET.start()

  collectors_by_name.clear()
  collectors_by_name['org.gnome.gsettings'] = GSettingsCollector()
  collectors_by_name['org.gnome.online-accounts'] = GoaCollector()

  return req.content, req.status_code

@app.route("/session/stop", methods=["POST"])
def session_stop():
  #FIXME: Make this a GET method by storing the host of the current session in session_start
  global VNC_WSOCKET
  data = dict(request.form)
  req = None

  VNC_WSOCKET.stop()

  #FIXME: Clear loggers
  #FIXME: Clear unsaved deploys
  try:
    req = requests.get("http://%s:8182/session/stop" % data['host'][0])
  except requests.exceptions.ConnectionError:
    return '{"status": "could not connect to host"}', 403

  return req.content, req.status_code

@app.route("/session/select", methods=["POST"])
def session_select():
  data = request.get_json()

  if not isinstance(data, dict):
    return '{"status": "bad JSON format"}'

  if not "sel" in data:
    return '{"status": "bad_form_data"}', 403

  selected_indices = [int(x) for x in data['sel']]
  collector = collectors_by_name['org.gnome.gsettings']
  collector.remember_selected(selected_indices)

  uid = str(uuid.uuid1().int)
  deploys[uid] = dict(collectors_by_name)
  collectors_by_name.clear()

  return json.dumps({"status": "ok", "uuid": uid})

def check_for_profile_index():
  INDEX_FILE = os.path.join(app.custom_args['profiles_dir'], "index.json")
  if os.path.isfile(INDEX_FILE):
    return

  try:
    open(INDEX_FILE, 'w+').write(json.dumps([]))
  except OSError:
    logging.error('There was an error attempting to write on %s' % INDEX_FILE)

def parse_config(config_file):
  SECTION_NAME = 'admin'
  args = {
      'host': 'localhost',
      'port': 8181,
      'profiles_dir': os.path.join(os.getcwd(), 'profiles'),
      'data_dir': os.getcwd(),
  }

  if not config_file:
    return args

  config = ConfigParser()
  try:
    config.read(config_file)
  except IOError:
    logging.warning('Could not find configuration file %s' % config_file)
  except ParsingError:
    logging.error('There was an error parsing %s' % config_file)
    sys.exit(1)
  except:
    logging.error('There was an unknown error parsing %s' % config_file)
    raise
    sys.exit(1)

  if not config.has_section(SECTION_NAME):
    return args

  def config_to_dict (config):
    res = {}
    for g in config.sections():
      res[g] = {}
      for o in config.options(g):
        res[g][o] = config.get(g, o)
    return res

  config = config_to_dict(config)
  args['host'] = config[SECTION_NAME].get('host', args['host'])
  args['port'] = config[SECTION_NAME].get('port', args['port'])
  args['profiles_dir'] = config[SECTION_NAME].get('profiles_dir', args['profiles_dir'])
  args['data_dir'] = config[SECTION_NAME].get('data_dir', args['data_dir'])

  try:
    args['port'] = int(args['port'])
  except ValueError:
    logging.error("Error reading configuration at %s: 'port' option must be an integer value")
    sys.exit(1)

  return args

if __name__ == "__main__":
  parser = ArgumentParser(description='Admin interface server')
  parser.add_argument(
    '--configuration', action='store', metavar='CONFIGFILE', default=None,
    help='Provide a configuration file path for the web service')

  args = parser.parse_args()
  app.custom_args = parse_config(args.configuration)
  app.template_folder = os.path.join(app.custom_args['data_dir'], 'templates')
  app.run(host=app.custom_args['host'], port=app.custom_args['port'], debug=True)
