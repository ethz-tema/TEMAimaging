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

from threading import Thread, Event

import wx
from pubsub import pub

from core.settings import Settings
from hardware.stage import Stage, AxisType


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
    def __init__(self, stage: Stage):
        super().__init__()
        self._stage = stage

    def run(self):
        self._run.clear()
        while not self._run.wait(Settings.get('stage.position_poll_rate')):
            pos = {
                AxisType.X: self._stage.axes[AxisType.X].position,
                AxisType.Y: self._stage.axes[AxisType.Y].position,
                AxisType.Z: self._stage.axes[AxisType.Z].position
            }
            wx.CallAfter(pub.sendMessage, 'stage.position_changed', position=pos)
