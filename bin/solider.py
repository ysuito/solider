#! /usr/bin/env python

import argparse
from pathlib import Path
import subprocess
import os
import pwd
import json
import glob

parser = argparse.ArgumentParser(description='A program to manage GUI applications running inside containers.')
parser.add_argument('command', choices=['start', 'build', 'build_all', 'update', 'entry', 'list'], help='command')
parser.add_argument('app_name', help='app name', nargs='?')

args = parser.parse_args()

home = os.environ['HOME']
soliderhome = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
src_path = os.path.join(soliderhome,'src/')
bin_path = os.path.join(soliderhome,'bin/')
desktopfile_dir = os.path.join(home,'.local/share/applications/')

base_command = [
  'docker', 'run',
  '--net=bridge',
  '--shm-size=4096m',
  '--rm',
  '-t',
  '-e', 'DISPLAY',
  '-e', 'XMODIFIERS',
  '-e', 'GTK_IM_MODULE',
  '-e', 'QT_IM_MODULE',
  '-e', 'DefalutIMModule=fcitx',
  '-e', 'PULSE_COOKIE=/tmp/pulse/cookie',
  '-e', 'PULSE_SERVER=unix:/tmp/pulse/native',
  '-e', 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus',
  '-v', '/run/user/1000/pulse/native:/tmp/pulse/native',
  '-v', os.path.join(home,'.config/pulse/cookie:/tmp/pulse/cookie:ro'),
  '-v', '/tmp/.X11-unix/X0:/tmp/.X11-unix/X0',
  '-v', '/run/user/1000/bus:/run/user/1000/bus',
  '-u', 'user',
]

class ContainerModel():

  type = ""
  command = []
  template = False
  privileged = False
  paths = []

  def __init__(self,json_path,name) -> None:
    with open(json_path,'r') as f:
      conf = json.load(f)
      self.type = conf['type']
      self.command = conf['command']
      self.template = conf['template']
      self.privileged = conf['privileged']
      self.base_image = conf['base_image']
      for path in conf['path']:
        if len(path) == 2:
          self.paths.append(path)
        else:
          print("{}'s path is invalid. path: {}".format(name, path))

class Ebuq():

  # Designs Structure
  # designs = {
  #   "CONTAINER_NAME": {
  #     "type": "disposal", // persistent, disposal
  #     "command": [
  #       "firefox-solider",  // container name
  #       "firefox", "--private-window", "--new-instance" // command
  #     ],
  #     "template": false, // build image
  #     "privileged": false, // Grant permissions. For example, when using a USB device.
  #     "path": [["host_path","container_path"]] // additional bind path
  #   }
  # }

  designs = {}

  def __init__(self) -> None:
    files = os.listdir(src_path)
    names = [f for f in files if os.path.isdir(os.path.join(src_path, f))]
    names = [name for name in names if not name.startswith(".")]
    for name in names:
      self.designs[name] = ContainerModel(
        os.path.join(src_path,name,'application.json'),
        name
      )

  def build_all(self):

    base_images = [name for name in self.designs.keys() if self.designs[name].base_image]
    app_images = [name for name in self.designs.keys() if not self.designs[name].base_image]

    # Build Base Container
    for name in self.designs.keys():
      design = self.designs[name]
      if name in base_images and design.template:
        base_path = os.path.join(soliderhome,name)
        command = ['docker', 'build', '--no-cache', '-t', name, base_path]
        subprocess.call(command)

    # Build App Container
    for name in self.designs.keys():
      design = self.designs[name]
      if name in app_images and design.template:
        app_path = os.path.join(src_path,name)
        args = ['docker', 'build', '--no-cache', '-t', name, app_path]
        subprocess.call(args)


  def build(self,name):
    design = self.designs[name]
    if design.template:
      app_path = os.path.join(src_path,name)
      args = ['docker', 'build', '--no-cache', '-t', name, app_path]
      subprocess.call(args)

  def start(self,name):
    design = self.designs[name]
    command = []
    if design.type == 'persistent':
      bind_path = os.path.join(soliderhome,'bind/',name)
      if not Path(bind_path).is_dir():
        os.makedirs(bind_path)
      command.extend(base_command)
      command.extend(['-v', '{}:/home/user/'.format(bind_path)])
      command.extend(['-e', 'HOME_HOST={}'.format(bind_path)])
    else:
      command.extend(base_command)

    for path in design.paths:
      command.extend(['-v', '{}:{}'.format(path[0],path[1])])

    if design.privileged:
      command.append('--privileged')

    command.extend(design.command)
    subprocess.Popen(command)


  def entry(self):
    for name in self.designs.keys():
      design = self.designs[name]
      if design.base_image:
        continue
      app_path = os.path.join(src_path,name)

      # Icon Specification
      icon_files = glob.glob(os.path.join(app_path,'*.png'))
      icon_files.extend(glob.glob(os.path.join(app_path,'*.svg')))
      icon_file = os.path.join(app_path, os.path.basename(icon_files[0])) if len(icon_files) > 0 else ''
      entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name={0}\n"
        "MimeType=application/vnd.ms-htmlhelp;\n"
        "Path={1}\n"
        "Exec=bash -c \"python3 solider.py start {0}\"\n"
        "NoDisplay=false\n"
        "Terminal=false\n"
        "StartupNotify=true\n"
        "Categories=Development;\n"
        "Icon={2}\n".format(name, bin_path, icon_file)
      )
      entry_file = os.path.join(desktopfile_dir,'{}.desktop'.format(name))
      with open(entry_file, 'w') as f:
        f.write(entry)
    command = ['update-desktop-database', desktopfile_dir]
    subprocess.call(command)

if __name__ == '__main__':
  solider = Ebuq()
  if args.command == 'start':
    solider.start(args.app_name)
  elif args.command == 'update':
    solider.build_all()
    solider.entry()
  elif args.command == 'build_all':
    solider.build_all()
    solider.entry()
  elif args.command == 'build':
    solider.build(args.app_name)
    solider.entry()
  elif args.command == 'entry':
    solider.entry()
  elif args.command == 'list':
    for name in solider.designs.keys():
      print(name)
