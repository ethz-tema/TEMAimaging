import os
import time
from importlib import import_module
from threading import Thread

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

        raise ValueError("Invalid driver name")

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

    def stop(self):
        self.alive = False
        self.join()


class CameraException(Exception):
    def __init__(self, fatal):
        self.fatal = fatal


for m in os.listdir('hardware/camera'):
    import_module('hardware.camera.{}'.format(m.split('.')[0]))
