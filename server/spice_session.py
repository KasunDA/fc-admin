#!/usr/bin/python3
#
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

import subprocess
import os
import time
import signal
import uuid

from flask import Flask

class SpiceSessionManager:
  XSPICE = 'Xspice :10 --disable-ticketing --port 8280'
  GNOME_SESSION = 'DISPLAY=:10 gnome-session'
  FCMDR_LOGGER = 'DISPLAY=:10 fcmdr-logger.py'
  WEBSOCKIFY = 'websockify localhost:8281 localhost:8280'

  def __init__(self):
    self.xspice = None
    self.gnome_session = None
    self.fcmdr_logger = None
    self.websockify = None

  def start(self):
    if self.xspice or self.gnome_session or self.fcmdr_logger or self.websockify:
      return False

    DNULL = open('/dev/null', 'w')
    template = "su -c \"%s\" - fc-user"
    self.xspice = subprocess.Popen(template % self.XSPICE, shell=True, stdout=DNULL, stderr=DNULL, stdin=DNULL)
    
    time.sleep(1)

    self.gnome_session    = subprocess.Popen(template % self.GNOME_SESSION,    shell=True, stdin=DNULL, stdout=DNULL, stderr=DNULL)
    self.fcmdr_logger = subprocess.Popen(template % self.FCMDR_LOGGER, shell=True, stdin=DNULL, stdout=DNULL, stderr=DNULL)
    self.websockify       = subprocess.Popen(template % self.WEBSOCKIFY,       shell=True, stdin=DNULL, stdout=DNULL, stderr=DNULL)
    return True

  def stop(self):
    #NOITE: This is a brute force approach to kill all fc-user processes
    subprocess.call ('pkill -u fc-user', shell=True)
    subprocess.call ('pkill -f "Xorg -config spiceqxl.xorg.conf -noreset :10"', shell=True)

    self.xspice = None
    self.gnome_session = None
    self.fcmdr_logger = None
    self.websockify = None

app = Flask(__name__)

has_session = False
spice = SpiceSessionManager()

@app.route("/start_session", methods=["GET"])
def new_session():
  global has_session
  global spice

  if has_session:
    return '{"status": "already_started"}', 403

  spice.start()

  has_session = True
  return '{"status": "ok"}', 200

@app.route("/stop_session")
def stop_session():
  global has_session
  global spice

  spice.stop()

  if not has_session:
    return '{"status": "already_stopped"}', 403

  has_session = False
  return '{"status": "stopped"}', 200

if __name__ == '__main__':  
  app.run(host='localhost', port=8182, debug=True)
