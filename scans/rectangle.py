import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class RectangleScan(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0.0, 1e-6),
                     'y_size': ('Y Size', 0.0, 1e-6),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1e-6),
                     'y_start': ('Y (Start)', 0.0, 1e-6),
                     'z_start': ('Z (Start)', 0.0, 1e-6)}

    display_name = "Rectangle Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, cleaning=False, cleaning_delay=0, x_size=1, y_size=1,
                 direction=0,
                 x_start=None, y_start=None, z_start=None, delta_z=None):
        self.x_steps = int(x_size / spot_size)
        self.y_steps = int(y_size / spot_size)
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.delta_z = delta_z
        self.shot_count = shot_count
        self.frequency = frequency
        self._curr_step = 0
        self._backwards = False
        self._steps = self.x_steps * self.y_steps
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params):
        return cls(spot_size, shot_count, frequency, cleaning, cleaning_delay, params['x_size'].value,
                   params['y_size'].value,
                   params['direction'].value, params['x_start'].value, params['y_start'].value,
                   params['z_start'].value)  # ,
        # params['delta_z'].value)

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
        if self._curr_step >= self._steps:
            return False

        self._curr_step += 1

        conn_mgr.trigger.go_and_wait(self._cleaning)

        if (self._curr_step + 1) % self.x_steps == 0:  # EOL
            dx = self.spot_size * math.sin(self.direction)
            dy = self.spot_size * math.cos(self.direction)
            self._backwards = not self._backwards
        else:
            dx = self.spot_size * math.cos(self.direction)
            dy = - self.spot_size * math.sin(self.direction)
            if self._backwards:
                dx = -dx
                dy = -dy

        conn_mgr.stage.move(MCSAxis.X, dx, relative=True, wait=False)
        conn_mgr.stage.move(MCSAxis.Y, dy, relative=True, wait=False)
        try:
            conn_mgr.stage.move(MCSAxis.Z, self.delta_z[self._curr_step], relative=True, wait=False)
        except ValueError:
            pass

        conn_mgr.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
