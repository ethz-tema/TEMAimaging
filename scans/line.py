import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class LineScan(metaclass=ScannerMeta):
    parameter_map = {'spot_count': ('Spot Count', 1, None),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'z_end': ('Z (End)', 0.0, 1000)}

    display_name = "Line Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, cleaning=False, cleaning_delay=0, spot_count=1,
                 direction=0, x_start=None,
                 y_start=None, z_start=None, delta_z=None):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.delta_z = delta_z
        self.shot_count = shot_count
        self.frequency = frequency

        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self._curr_step = 0
        self._dx = math.sin(self.direction) * self.spot_size
        self._dy = math.cos(self.direction) * self.spot_size

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, cleaning_delay, params):
        spot_count = params['spot_count'].value
        if spot_count > 1 and params['z_start'].value and params['z_end']:
            dz = (params['z_end'].value - params['z_start'].value) / (spot_count - 1)
            dz_list = [dz] * (spot_count - 1)
        else:
            dz_list = []

        return cls(spot_size, shot_count, frequency, cleaning, cleaning_delay, spot_count, params['direction'].value,
                   params['x_start'].value, params['y_start'].value, params['z_start'].value, dz_list)

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
        if self._curr_step >= self.spot_count:
            return False

        conn_mgr.trigger.go_and_wait(self._cleaning, self._cleaning_delay)

        if self._curr_step + 1 >= self.spot_count:  # skip move after last shot
            return False

        conn_mgr.stage.move(MCSAxis.X, self._dx, relative=True, wait=False)
        conn_mgr.stage.move(MCSAxis.Y, self._dy, relative=True, wait=False)
        try:
            conn_mgr.stage.move(MCSAxis.Z, self.delta_z[self._curr_step], relative=True, wait=False)
        except ValueError:
            pass

        self._curr_step += 1
        conn_mgr.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
