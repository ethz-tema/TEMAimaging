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

import math
from threading import Event

from tema_imaging.core.conn_mgr import conn_mgr
from tema_imaging.core.scanner_registry import ScannerMeta
from tema_imaging.hardware.stage import AxisType, AxisMovementMode
from tema_imaging.scans import Spot


class ContinuousLineScan(metaclass=ScannerMeta):
    parameter_map = {'spot_count': ('Spot Count', 1, None),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'z_end': ('Z (End)', 0.0, 1000)}

    display_name = "Cont. Line Scan"

    def __init__(self, spot_size, shots_per_spot=1, frequency=1, _=None, spot_count=1, direction=0, x_start=None,
                 y_start=None, z_start=None, dz=None):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.shots_per_spot = shots_per_spot
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.frequency = frequency

        self._vx = math.sin(self.direction) * self.spot_size * self.frequency / shots_per_spot
        self._vy = math.cos(self.direction) * self.spot_size * self.frequency / shots_per_spot

        v = math.sqrt(math.pow(self._vx, 2) + math.pow(self._vy, 2))

        self._dx = math.sin(self.direction) * self.spot_size * spot_count
        self._dy = math.cos(self.direction) * self.spot_size * spot_count
        self._dz = dz

        time = spot_size * spot_count / v
        self._vz = dz / time

        self.on_frame_completed_event = Event()
        self.movement_completed_event = Event()

    @classmethod
    def from_params(cls, spot_size, shots_per_spot, frequency, cleaning, _, params):
        spot_count = params['spot_count'].value

        if spot_count > 1 and params['z_start'].value and params['z_end']:
            dz = params['z_end'].value - params['z_start'].value
        else:
            dz = 0

        return cls(spot_size, shots_per_spot, frequency, cleaning, spot_count, params['direction'].value,
                   params['x_start'].value, params['y_start'].value, params['z_start'].value, dz)

    @property
    def boundary_size(self):
        return self._dx, self._dy

    def init_scan(self, _):
        conn_mgr.stage.on_movement_completed += self.on_movement_completed

        conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE

        moved = False
        if self.x_start is not None:
            conn_mgr.stage.axes[AxisType.X].move(self.x_start, False)
            moved = True
        if self.y_start is not None:
            conn_mgr.stage.axes[AxisType.Y].move(self.y_start, False)
            moved = True
        if self.z_start is not None:
            conn_mgr.stage.axes[AxisType.Z].move(self.z_start, False)
            moved = True

        conn_mgr.stage.commit_move()

        conn_mgr.trigger.set_count(self.spot_count * self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(False)

        if moved:
            self.movement_completed_event.wait()
            self.movement_completed_event.clear()

        conn_mgr.stage.on_movement_completed -= self.on_movement_completed

        if self._vx != 0:
            conn_mgr.stage.axes[AxisType.X].speed = abs(self._vx)
        if self._vy != 0:
            conn_mgr.stage.axes[AxisType.Y].speed = abs(self._vy)
        if self._vz != 0:
            conn_mgr.stage.axes[AxisType.Z].speed = abs(self._vz)

        conn_mgr.stage.on_frame_completed += self.on_frame_completed
        conn_mgr.stage.movement_queue.put(
            Spot(self.x_start + self._dx, self.y_start + self._dy, self.z_start + self._dz))

    def next_move(self):
        if not self.spot_count:
            return False

        conn_mgr.trigger.go()

        conn_mgr.stage.trigger_frame()

        self.on_frame_completed_event.wait()
        self.on_frame_completed_event.clear()
        return False

    def next_shot(self):
        pass

    def done(self):
        conn_mgr.stage.on_frame_completed -= self.on_frame_completed

    def on_frame_completed(self):
        self.on_frame_completed_event.set()

    def on_movement_completed(self):
        self.movement_completed_event.set()
