import wx
from wx.lib.pubsub import pub


class LaserStatusChangedEvent(wx.PyCommandEvent):
    def __init__(self, evt_type, _id, status):
        super().__init__(evt_type, _id)

        self.status = status


class LaserStatusPoller(wx.Timer):
    def __init__(self, panel, laser, *args, **kw):
        super().__init__(*args, **kw)
        self._laser_panel = panel
        self._laser = laser

    def Notify(self):
        pub.sendMessage('laser.status_changed', status=self._laser.opmode)


class ShutterStatusPoller(wx.Timer):
    def __init__(self, panel, shutter, *args, **kw):
        super().__init__(*args, **kw)
        self._laser_panel = panel
        self._shutter = shutter

    def Notify(self):
        pub.sendMessage('shutter.status_changed', status=self._shutter.status)
