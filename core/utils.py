import time
from threading import Thread

import wx
from wx.lib.pubsub import pub

from core.settings import Settings


class LaserStatusPoller(wx.Timer):
    def __init__(self, laser, *args, **kw):
        super().__init__(*args, **kw)
        self._laser = laser

    def Notify(self):
        pub.sendMessage('laser.status_changed', status=self._laser.opmode)


class ShutterStatusPoller(wx.Timer):
    def __init__(self, shutter, *args, **kw):
        super().__init__(*args, **kw)
        self._shutter = shutter

    def Notify(self):
        pub.sendMessage('shutter.status_changed', status=self._shutter.status)


class StagePositionPoller(Thread):
    def __init__(self, stage, *args, **kw):
        super().__init__(*args, **kw)
        self._stage = stage
        self._run = True

    def run(self):
        self._run = True
        while self._run:
            time.sleep(Settings.get('stage.position_poll_rate'))
            wx.CallAfter(pub.sendMessage, 'stage.position_changed', position=self._stage.get_position())

    def stop(self):
        self._run = False
        self.join()
