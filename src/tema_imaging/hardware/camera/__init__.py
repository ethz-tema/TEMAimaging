# This file is part of the TEMAimaging project.
# Copyright (c) 2020, ETH Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import os
import time
from importlib import import_module
from threading import Thread

from tema_imaging.core.utils import get_project_root

camera_resolutions = {
    "640x480": (640, 480),
    "720x576": (720, 576),
    "1280x1024": (1280, 1024),
    "1920x1080": (1920, 1080)
}


class Camera:
    driver_name = None

    @staticmethod
    def get_driver_from_name(name):
        subs = Camera.__subclasses__()
        for klass in subs:
            if klass.driver_name == name:
                return klass

        raise ValueError(f"Invalid driver name '{name}'")

    def __init__(self):
        pass

    def init(self):
        pass

    @staticmethod
    def get_device_ids():
        pass


class CameraThread(Thread):
    def __init__(self, camera, notify, timeout=100):
        super(CameraThread, self).__init__()
        self.alive = True
        self.camera = camera
        self.notify = notify
        self.timeout = timeout

    def run(self):
        while self.alive:
            # ignore image transfer errors
            try:
                image = self.camera.get_frame()
                self.notify(self.camera, image)
            except CameraException as e:
                if e.fatal:
                    raise e
            if self.camera.driver_name == 'v4l2':
                time.sleep(1 / 30)  # TODO: Fix this; sleep a bit so the UI thread has time to process

    def stop(self):
        self.alive = False
        self.join()


class CameraException(Exception):
    def __init__(self, fatal):
        self.fatal = fatal


for m in os.listdir(get_project_root() / 'src/tema_imaging/hardware/camera'):
    try:
        import_module('tema_imaging.hardware.camera.{}'.format(m.split('.')[0]))
    except ImportError:
        pass

