import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class ContinuousRectangleScan(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0, 1000),
                     'y_size': ('Y Size', 0, 1000),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'zig_zag_mode': ('Zig Zag', False, None)}

    display_name = "Cont. Rectangle Scan"

    def __init__(self, spot_size, shots_per_spot=1, frequency=1, _=None, x_size=1, y_size=1, direction=0,
                 x_start=None, y_start=None, z_start=None, zig_zag_mode=False):
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
        self._vx = math.cos(self.direction) * self.spot_size * self.frequency / shots_per_spot
        self._vy = math.sin(self.direction) * self.spot_size * self.frequency / shots_per_spot

        self._dx = math.cos(self.direction) * self.spot_size * self.x_steps
        self._dy = math.sin(self.direction) * self.spot_size * self.y_steps

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, _, params):
        return cls(spot_size, shot_count, frequency, cleaning, params['x_size'].value, params['y_size'].value,
                   params['direction'].value, params['x_start'].value, params['y_start'].value,
                   params['z_start'].value, params['zig_zag_mode'].value)

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
        conn_mgr.trigger.set_count(self.shot_count)
        conn_mgr.trigger.set_freq(self.frequency)

        conn_mgr.stage.wait_until_status()

    def next_move(self):
        if self._curr_line >= self.y_steps:
            return False

        self._curr_line += 1

        if self._vx != 0:
            conn_mgr.stage.set_speed(self._vx, MCSAxis.X)
        if self._vy != 0:
            conn_mgr.stage.set_speed(self._vy, MCSAxis.Y)

        if self._dx != 0:
            conn_mgr.stage.move(MCSAxis.X, self._dx, relative=True, wait=False)
        if self._dy != 0:
            conn_mgr.stage.move(MCSAxis.Y, self._dy, relative=True, wait=False)

        conn_mgr.trigger.go()

        conn_mgr.stage.wait_until_status()

        conn_mgr.stage.set_speed(0)
        conn_mgr.stage.move(MCSAxis.Y, self.spot_size, relative=True, wait=False)

        if self.zig_zag_mode:
            self._dx = -self._dx
            self._dy = -self._dy
        else:
            conn_mgr.stage.move(MCSAxis.X, -self.x_steps * self.spot_size, relative=True, wait=False)

        conn_mgr.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
