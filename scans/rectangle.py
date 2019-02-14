import math
import time
from typing import List

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.stage.mcs_stage import MCSAxis
from scans import Spot


class RectangleScan(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0, 1000),
                     'y_size': ('Y Size', 0, 1000),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'zig_zag_mode': ('Zig Zag', False, None),
                     'blank_lines': ('# of blank lines', 0, None)}

    display_name = "Rectangle Scan"

    def __init__(self, spot_size, shots_per_spot=1, frequency=1, cleaning=False, cleaning_delay=0, x_size=1, y_size=1,
                 direction=0,
                 x_start=None, y_start=None, z_start=None, zig_zag_mode=False, blank_lines=0):
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

        self.coord_list = []  # type: List[Spot]
        self.coord_list.append(Spot(x_start, y_start))

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

            dx = round(spot_size * (math.cos(self.direction) * x_step + math.sin(self.direction) * y_step))
            dy = round(spot_size * (math.cos(self.direction) * y_step - math.sin(self.direction) * x_step))

            prev_spot = self.coord_list[i - 1]
            self.coord_list.append(Spot(prev_spot.X + dx, prev_spot.Y + dy))

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params):
        return cls(spot_size, shot_count, frequency, cleaning, cleaning_delay, params['x_size'].value,
                   params['y_size'].value,
                   params['direction'].value, params['x_start'].value, params['y_start'].value,
                   params['z_start'].value, params['zig_zag_mode'].value, params['blank_lines'].value)

    @property
    def boundary_size(self):
        x = max(spot.X for spot in self.coord_list) - min(spot.X for spot in self.coord_list) + self.spot_size
        y = max(spot.Y for spot in self.coord_list) - min(spot.Y for spot in self.coord_list) + self.spot_size

        return x, y

    def init_scan(self, measurement):
        self.blank_delay = measurement.blank_delay

        if self.z_start:
            conn_mgr.stage.move(MCSAxis.Z, self.z_start, wait=False)

        conn_mgr.trigger.set_count(self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        conn_mgr.stage.wait_until_status()

    def next_move(self):
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

        spot = self.coord_list[self._curr_step]

        move_x = False
        move_y = False
        if self._curr_step > 0:
            prev_spot = self.coord_list[self._curr_step - 1]

            if spot.X - prev_spot.X != 0:
                move_x = True
            if spot.Y - prev_spot.Y != 0:
                move_y = True
        else:
            move_x = True
            move_y = True

        axes_to_check = []
        if move_x:
            conn_mgr.stage.move(MCSAxis.X, spot.X, wait=False)
            axes_to_check.append(MCSAxis.X)
        if move_y:
            conn_mgr.stage.move(MCSAxis.Y, spot.Y, wait=False)
            axes_to_check.append(MCSAxis.Y)

        conn_mgr.stage.wait_until_status(axes_to_check)

        conn_mgr.trigger.go_and_wait(self._cleaning, self._cleaning_delay)

        self._curr_step += 1
        return True

    def next_shot(self):
        pass
