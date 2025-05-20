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
class LineScan(Scan):
    parameter_map = {
        "spot_count": ("Spot Count", 1, None),
        "direction": ("Direction", 0.0, None),
        "x_start": ("X (Start)", 0.0, 1000),
        "y_start": ("Y (Start)", 0.0, 1000),
        "z_start": ("Z (Start)", 0.0, 1000),
        "z_end": ("Z (End)", 0.0, 1000),
        "blank_spots": ("# of blank spots", 0, None),
    }

    display_name = "Line Scan"

    def __init__(
        self,
        spot_size,
        shots_per_spot=1,
        frequency=1,
        cleaning=False,
        cleaning_delay=0,
        spot_count=1,
        direction=0,
        x_start=None,
        y_start=None,
        z_start=None,
        z_end=None,
        blank_spots=0,
    ):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.shots_per_spot = shots_per_spot
        self.frequency = frequency
        self.blank_spots = blank_spots
        self.blank_delay = 0
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.z_end = z_end
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay

        self._curr_step = 0

        self.coord_list: list[Spot] = []

        if spot_count <= 1:
            dz = 0
        else:
            dz = (z_end - z_start) / (spot_count - 1)

        for i in range(spot_count):
            x = round(x_start + math.sin(self.direction) * spot_size * i)
            y = round(y_start + math.cos(self.direction) * spot_size * i)
            z = round(z_start + dz * i)

            self.coord_list.append(Spot(x, y, z))

        self.movement_completed_event = Event()

    @classmethod
    def from_params(
        cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params
    ):
        spot_count = params["spot_count"].value

        return cls(
            spot_size,
            shot_count,
            frequency,
            cleaning,
            cleaning_delay,
            spot_count,
            params["direction"].value,
            params["x_start"].value,
            params["y_start"].value,
            params["z_start"].value,
            params["z_end"].value,
            params["blank_spots"].value,
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

        conn_mgr.trigger.set_count(self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE

    def next_move(self) -> bool:
        if self._curr_step >= len(self.coord_list):
            return False

        if self.blank_spots:
            time.sleep(self.blank_delay / 1000)
            conn_mgr.trigger.single_tof()
            self.blank_spots -= 1
            return True

        spot = self.coord_list[self._curr_step]

        move_x = False
        move_y = False
        move_z = False
        if self._curr_step > 0:
            prev_spot = self.coord_list[self._curr_step - 1]

            if spot.X - prev_spot.X != 0:
                move_x = True
            if spot.Y - prev_spot.Y != 0:
                move_y = True
            if spot.Z - prev_spot.Z != 0:
                move_z = True
        else:
            move_x = True
            move_y = True
            move_z = True

        if move_x:
            conn_mgr.stage.axes[AxisType.X].move(spot.X, False)
        if move_y:
            conn_mgr.stage.axes[AxisType.Y].move(spot.Y, False)
        if move_z:
            conn_mgr.stage.axes[AxisType.Z].move(spot.Z, False)

        conn_mgr.stage.commit_move()

        self.movement_completed_event.wait()
        self.movement_completed_event.clear()

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
        conn_mgr.stage.on_movement_completed -= self.on_movement_completed

    def on_movement_completed(self) -> None:
        self.movement_completed_event.set()
