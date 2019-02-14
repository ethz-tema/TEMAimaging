import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.stage.mcs_stage import MCSAxis


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

        self._curr_step = 0
        self._vx = math.sin(self.direction) * self.spot_size * self.frequency / shots_per_spot
        self._vy = math.cos(self.direction) * self.spot_size * self.frequency / shots_per_spot

        v = math.sqrt(math.pow(self._vx, 2) + math.pow(self._vy, 2))

        self._dx = math.sin(self.direction) * self.spot_size * spot_count
        self._dy = math.cos(self.direction) * self.spot_size * spot_count
        self._dz = dz

        time = spot_size * spot_count / v
        self._vz = dz / time

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
        if self.x_start is not None:
            conn_mgr.stage.move(MCSAxis.X, self.x_start, wait=False)
        if self.y_start is not None:
            conn_mgr.stage.move(MCSAxis.Y, self.y_start, wait=False)
        if self.z_start is not None:
            conn_mgr.stage.move(MCSAxis.Z, self.z_start, wait=False)
        conn_mgr.trigger.set_count(self.spot_count * self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(False)

        conn_mgr.stage.wait_until_status()

        if self._vx != 0:
            conn_mgr.stage.set_speed(abs(self._vx), MCSAxis.X)
        if self._vy != 0:
            conn_mgr.stage.set_speed(abs(self._vy), MCSAxis.Y)
        if self._vz != 0:
            conn_mgr.stage.set_speed(abs(self._vz), MCSAxis.Z)

    def next_move(self):
        if self._curr_step >= self.spot_count:
            return False

        conn_mgr.trigger.go()

        if self._curr_step + 1 >= self.spot_count:  # skip move after last shot
            return False

        if self._dx != 0:
            conn_mgr.stage.move(MCSAxis.X, self._dx, relative=True, wait=False)
        if self._dy != 0:
            conn_mgr.stage.move(MCSAxis.Y, self._dy, relative=True, wait=False)
        if self._dz != 0:
            conn_mgr.stage.move(MCSAxis.Z, self._dz, relative=True, wait=False)

        self._curr_step += 1
        conn_mgr.stage.wait_until_status()

        conn_mgr.stage.set_speed(0)
        return False

    def next_shot(self):
        pass
