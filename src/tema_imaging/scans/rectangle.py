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
import time
from threading import Event

from tema_imaging.core.conn_mgr import conn_mgr
from tema_imaging.core.measurement import Measurement
from tema_imaging.core.scanner_registry import register_scan
from tema_imaging.hardware.stage import AxisMovementMode, AxisType
from tema_imaging.scans import Scan, Spot


@register_scan
class RectangleScan(Scan):
    parameter_map = {
        "x_size": ("X Size", 0, 1000),
        "y_size": ("Y Size", 0, 1000),
        "direction": ("Direction", 0.0, None),
        "x_start": ("X (Start)", 0.0, 1000),
        "y_start": ("Y (Start)", 0.0, 1000),
        "z_start": ("Z (Start)", 0.0, 1000),
        "zig_zag_mode": ("Zig Zag", False, None),
        "blank_lines": ("# of blank lines", 0, None),
    }

    display_name = "Rectangle Scan"

    def __init__(
        self,
        spot_size,
        shots_per_spot=1,
        frequency=1,
        cleaning=False,
        cleaning_delay=0,
        x_size=1,
        y_size=1,
        direction=0,
        x_start=None,
        y_start=None,
        z_start=None,
        zig_zag_mode=False,
        blank_lines=0,
    ) -> None:
        self.x_steps = x_size // spot_size
        self.y_steps = y_size // spot_size
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.shots_per_spot = shots_per_spot
        self.frequency = frequency

        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self.blank_spots = blank_lines * self.x_steps
        self.blank_delay = 0

        self._curr_step = 0
        self._curr_blank = 0

        self.coord_list: list[Spot] = []
        self.coord_list.append(Spot(x_start, y_start))
        conn_mgr.stage.movement_queue.put(Spot(x_start, y_start))

        steps = self.x_steps * self.y_steps

        backwards = False
        for i in range(1, steps):
            if i % self.x_steps == 0:  # EOL
                if zig_zag_mode:
                    x_step = 0
                    y_step = 1
                    backwards = not backwards
                else:
                    x_step = -self.x_steps + 1
                    y_step = 1
            else:
                x_step = 1 if not backwards else -1
                y_step = 0

            dx = round(
                spot_size
                * (
                    math.cos(self.direction) * x_step
                    + math.sin(self.direction) * y_step
                )
            )
            dy = round(
                spot_size
                * (
                    math.cos(self.direction) * y_step
                    - math.sin(self.direction) * x_step
                )
            )

            prev_spot = self.coord_list[i - 1]
            spot = Spot(prev_spot.X + dx, prev_spot.Y + dy)
            self.coord_list.append(spot)
            conn_mgr.stage.movement_queue.put(
                spot
            )  # TODO: move this to init_scan since it modifies hardware state

        self.frame_event = Event()
        self.movement_completed_event = Event()

    @classmethod
    def from_params(
        cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params
    ):
        return cls(
            spot_size,
            shot_count,
            frequency,
            cleaning,
            cleaning_delay,
            params["x_size"].value,
            params["y_size"].value,
            params["direction"].value,
            params["x_start"].value,
            params["y_start"].value,
            params["z_start"].value,
            params["zig_zag_mode"].value,
            params["blank_lines"].value,
        )

    @property
    def boundary_size(self) -> tuple[float, float]:
        x = (
            max(spot.X for spot in self.coord_list)
            - min(spot.X for spot in self.coord_list)
            + self.spot_size
        )
        y = (
            max(spot.Y for spot in self.coord_list)
            - min(spot.Y for spot in self.coord_list)
            + self.spot_size
        )

        return x, y

    def _init_scan(self, measurement: Measurement) -> None:
        conn_mgr.stage.on_movement_completed += self.on_movement_completed

        self.blank_delay = measurement.blank_delay

        conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE

        conn_mgr.stage.on_frame_completed += self.on_frame_completed

        if self.z_start:
            conn_mgr.stage.axes[AxisType.Z].move(self.z_start)

        conn_mgr.trigger.set_count(self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        if self.z_start:
            self.movement_completed_event.wait()
            self.movement_completed_event.clear()

        conn_mgr.stage.on_movement_completed -= self.on_movement_completed

    def next_move(self) -> bool:
        if self._curr_step >= len(self.coord_list):
            return False

        if self.blank_spots:
            if self._curr_blank == 0:
                time.sleep(self.blank_delay / 1000)
            conn_mgr.trigger.single_tof()
            self.blank_spots -= 1
            self._curr_blank += 1
            time.sleep(self.blank_delay / 1000)
            return True

        conn_mgr.stage.trigger_frame()

        self.frame_event.wait()
        self.frame_event.clear()

        curr_pos = Spot(
            conn_mgr.stage.axes[AxisType.X].position,
            conn_mgr.stage.axes[AxisType.Y].position,
            conn_mgr.stage.axes[AxisType.Z].position,
        )
        self.log_spot(curr_pos)
        conn_mgr.trigger.go_and_wait(self._cleaning, self._cleaning_delay)

        self._curr_step += 1
        return True

    def next_shot(self) -> None:
        pass

    def done(self) -> None:
        conn_mgr.stage.on_frame_completed -= self.on_frame_completed

    def on_frame_completed(self) -> None:
        self.frame_event.set()

    def on_movement_completed(self) -> None:
        self.movement_completed_event.set()
