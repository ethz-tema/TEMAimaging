from threading import Thread, Event

import wx
from wx.lib.pubsub import pub

from core.settings import Settings


class StatusPoller(Thread):
    def __init__(self):
        super().__init__()
        self._run = Event()

    def run(self):
        raise NotImplementedError

    def stop(self):
        self._run.set()
        self.join()


class LaserStatusPoller(StatusPoller):
    def __init__(self, laser):
        super().__init__()
        self._laser = laser

    def run(self):
        self._run.clear()
        while not self._run.wait(0.7):
            wx.CallAfter(pub.sendMessage, 'laser.status_changed', status=self._laser.opmode)
            wx.CallAfter(pub.sendMessage, 'laser.hv_changed', hv=self._laser.hv)
            wx.CallAfter(pub.sendMessage, 'laser.egy_changed', egy=self._laser.egy)


class ShutterStatusPoller(StatusPoller):
    def __init__(self, shutter):
        super().__init__()
        self._shutter = shutter

    def run(self):
        self._run.clear()
        while not self._run.wait(1):
            wx.CallAfter(pub.sendMessage, 'shutter.status_changed', open=self._shutter.status)


class StagePositionPoller(StatusPoller):
    def __init__(self, stage):
        super().__init__()
        self._stage = stage

    def run(self):
        self._run.clear()
        while not self._run.wait(Settings.get('stage.position_poll_rate')):
            wx.CallAfter(pub.sendMessage, 'stage.position_changed', position=self._stage.get_position())
