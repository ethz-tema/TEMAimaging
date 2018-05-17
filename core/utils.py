import time
from threading import Thread

import wx
from wx.lib.pubsub import pub

from core.settings import Settings


class StatusPoller(Thread):
    def __init__(self):
        super().__init__()
        self._run = False

    def run(self):
        raise NotImplementedError

    def stop(self):
        self._run = False
        self.join()


class LaserStatusPoller(StatusPoller):
    def __init__(self, laser):
        super().__init__()
        self._laser = laser

    def run(self):
        self._run = True
        while self._run:
            time.sleep(0.7)
            wx.CallAfter(pub.sendMessage, 'laser.status_changed', status=self._laser.opmode)
            wx.CallAfter(pub.sendMessage, 'laser.hv_changed', hv=self._laser.hv)
            wx.CallAfter(pub.sendMessage, 'laser.egy_changed', egy=self._laser.egy)


class ShutterStatusPoller(StatusPoller):
    def __init__(self, shutter):
        super().__init__()
        self._shutter = shutter

    def run(self):
        self._run = True
        while self._run:
            time.sleep(1)
            wx.CallAfter(pub.sendMessage, 'shutter.status_changed', status=self._shutter.status)


class StagePositionPoller(StatusPoller):
    def __init__(self, stage):
        super().__init__()
        self._stage = stage

    def run(self):
        self._run = True
        while self._run:
            time.sleep(Settings.get('stage.position_poll_rate'))
            wx.CallAfter(pub.sendMessage, 'stage.position_changed', position=self._stage.get_position())
