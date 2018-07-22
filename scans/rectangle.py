import math
import time

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


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
        self.x_size = x_size
        self.y_size = y_size
        self.x_steps = x_size // spot_size
        self.y_steps = y_size // spot_size
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.shots_per_spot = shots_per_spot
        self.frequency = frequency
        self._curr_step = 0
        self._backwards = False
        self._steps = self.x_steps * self.y_steps
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self.zig_zag_mode = zig_zag_mode
        self.blank_spots = blank_lines * self.x_steps

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params):
        return cls(spot_size, shot_count, frequency, cleaning, cleaning_delay, params['x_size'].value,
                   params['y_size'].value,
                   params['direction'].value, params['x_start'].value, params['y_start'].value,
                   params['z_start'].value, params['zig_zag_mode'].value, params['blank_lines'].value)

    @property
    def boundary_size(self):
        if self.direction in [0, 90, 180, 270]:
            return self.x_size, self.y_size
        # TODO: rotated rectangle
        return 0, 0

    def init_scan(self):
        if self.x_start:
            conn_mgr.stage.move(MCSAxis.X, self.x_start, wait=False)
        if self.y_start:
            conn_mgr.stage.move(MCSAxis.Y, self.y_start, wait=False)
        if self.z_start:
            conn_mgr.stage.move(MCSAxis.Z, self.z_start, wait=False)
        conn_mgr.trigger.set_count(self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        conn_mgr.stage.wait_until_status()

    def next_move(self):
        if self._curr_step >= self._steps:
            return False

        if self.blank_spots:
            conn_mgr.trigger.single_tof()
            self.blank_spots -= 1
            time.sleep(0.3)
            return True

        self._curr_step += 1

        conn_mgr.trigger.go_and_wait(self._cleaning, self._cleaning_delay)

        if self._curr_step % self.x_steps == 0:  # EOL
            if self.zig_zag_mode:
                x_step = 0
                y_step = 1
                self._backwards = not self._backwards
            else:
                x_step = -self.x_steps + 1
                y_step = 1
        else:
            x_step = 1 if not self._backwards else -1
            y_step = 0

        dx = self.spot_size * (math.cos(self.direction) * x_step + math.sin(self.direction) * y_step)
        dy = self.spot_size * (math.cos(self.direction) * y_step - math.sin(self.direction) * x_step)

        conn_mgr.stage.move(MCSAxis.X, dx, relative=True, wait=False)
        conn_mgr.stage.move(MCSAxis.Y, dy, relative=True, wait=False)

        conn_mgr.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
