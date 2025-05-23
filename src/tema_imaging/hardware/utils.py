from threading import Event, Thread

import wx
from pubsub import pub

from tema_imaging.core.settings import Settings
from tema_imaging.hardware.laser_compex import CompexLaserProtocol
from tema_imaging.hardware.shutter import Shutter
from tema_imaging.hardware.stage import AxisType, Stage


class StatusPoller(Thread):
    def __init__(self) -> None:
        super().__init__()
        self._run = Event()

    def run(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        self._run.set()
        self.join()


class LaserStatusPoller(StatusPoller):
    def __init__(self, laser: CompexLaserProtocol) -> None:
        super().__init__()
        self._laser = laser

    def run(self) -> None:
        self._run.clear()
        while not self._run.wait(0.7):
            wx.CallAfter(
                pub.sendMessage, "laser.status_changed", status=self._laser.opmode
            )
            wx.CallAfter(pub.sendMessage, "laser.hv_changed", hv=self._laser.hv)
            wx.CallAfter(pub.sendMessage, "laser.egy_changed", egy=self._laser.egy)


class ShutterStatusPoller(StatusPoller):
    def __init__(self, shutter: Shutter) -> None:
        super().__init__()
        self._shutter = shutter

    def run(self) -> None:
        self._run.clear()
        while not self._run.wait(1):
            wx.CallAfter(
                pub.sendMessage, "shutter.status_changed", open=self._shutter.status
            )


class StagePositionPoller(StatusPoller):
    def __init__(self, stage: Stage) -> None:
        super().__init__()
        self._stage = stage

    def run(self) -> None:
        self._run.clear()
        while not self._run.wait(Settings.get("stage.position_poll_rate")):
            pos = {
                AxisType.X: self._stage.axes[AxisType.X].position,
                AxisType.Y: self._stage.axes[AxisType.Y].position,
                AxisType.Z: self._stage.axes[AxisType.Z].position,
            }
            wx.CallAfter(pub.sendMessage, "stage.position_changed", position=pos)
