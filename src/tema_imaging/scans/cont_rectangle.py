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
from tema_imaging.core.measurement import Measurement
from tema_imaging.core.scanner_registry import register_scan
from tema_imaging.hardware.stage import AxisType, AxisMovementMode
from tema_imaging.scans import Scan


@register_scan
class ContinuousRectangleScan(Scan):
    parameter_map = {
        "x_size": ("X Size", 0, 1000),
        "y_size": ("Y Size", 0, 1000),
        "direction": ("Direction", 0.0, None),
        "x_start": ("X (Start)", 0.0, 1000),
        "y_start": ("Y (Start)", 0.0, 1000),
        "z_start": ("Z (Start)", 0.0, 1000),
        "zig_zag_mode": ("Zig Zag", False, None),
    }

    display_name = "Cont. Rectangle Scan"

    def __init__(
        self,
        spot_size,
        shots_per_spot=1,
        frequency=1,
        _=None,
        x_size=1,
        y_size=1,
        direction=0,
        x_start=None,
        y_start=None,
        z_start=None,
        zig_zag_mode=False,
    ):
        self.x_size = x_size
        self.y_size = y_size
        self.x_steps = x_size // spot_size
        self.y_steps = y_size // spot_size
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.shot_count = self.x_steps * shots_per_spot
        self.frequency = frequency
        self._backwards = False
        self._steps = self.x_steps * self.y_steps
        self.zig_zag_mode = zig_zag_mode

        self._curr_line = 0
        self._vx = (
            math.cos(self.direction) * self.spot_size * self.frequency / shots_per_spot
        )
        self._vy = (
            math.sin(self.direction) * self.spot_size * self.frequency / shots_per_spot
        )

        self._dx = math.cos(self.direction) * self.spot_size * self.x_steps
        self._dy = math.sin(self.direction) * self.spot_size * self.y_steps

        self.movement_completed_event = Event()

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, _, params):
        return cls(
            spot_size,
            shot_count,
            frequency,
            cleaning,
            params["x_size"].value,
            params["y_size"].value,
            params["direction"].value,
            params["x_start"].value,
            params["y_start"].value,
            params["z_start"].value,
            params["zig_zag_mode"].value,
        )

    @property
    def boundary_size(self) -> tuple[float, float]:
        if self.direction in [0, 90, 180, 270]:
            return self.x_size, self.y_size
        # TODO: rotated rectangle
        return 0, 0

    def _init_scan(self, _: Measurement) -> None:
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

        conn_mgr.trigger.set_count(self.shot_count)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(False)

        if moved:
            self.movement_completed_event.wait()
            self.movement_completed_event.clear()

        conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_RELATIVE
        conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_RELATIVE

    def next_move(self) -> bool:
        if self._curr_line >= self.y_steps:
            return False

        self._curr_line += 1

        if self._vx != 0:
            conn_mgr.stage.axes[AxisType.X].speed = abs(self._vx)
        if self._vy != 0:
            conn_mgr.stage.axes[AxisType.Y].speed = abs(self._vy)

        if self._dx != 0:
            conn_mgr.stage.axes[AxisType.X].move(self._dx, False)
        if self._dy != 0:
            conn_mgr.stage.axes[AxisType.Y].move(self._dy, False)

        conn_mgr.stage.commit_move()

        conn_mgr.trigger.go()

        self.movement_completed_event.wait()
        self.movement_completed_event.clear()

        conn_mgr.stage.axes[AxisType.X].speed = 0
        conn_mgr.stage.axes[AxisType.Y].speed = 0

        conn_mgr.stage.axes[AxisType.Y].move(self.spot_size, False)

        if self.zig_zag_mode:
            self._dx = -self._dx
            self._dy = -self._dy
        else:
            conn_mgr.stage.axes[AxisType.X].move(-self.x_steps * self.spot_size, False)

        conn_mgr.stage.commit_move()

        self.movement_completed_event.wait()
        self.movement_completed_event.clear()
        return True

    def next_shot(self) -> None:
        pass

    def done(self) -> None:
        conn_mgr.stage.on_movement_completed -= self.on_movement_completed

    def on_movement_completed(self) -> None:
        self.movement_completed_event.set()
