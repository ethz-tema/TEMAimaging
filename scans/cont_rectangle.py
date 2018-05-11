import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class ContinuousRectangleScan(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0.0, 1e-6),
                     'y_size': ('Y Size', 0.0, 1e-6),
                     'direction': ('Direction', 0.0, None),
                     'x_start': ('X (Start)', 0.0, 1e-6),
                     'y_start': ('Y (Start)', 0.0, 1e-6),
                     'z_start': ('Z (Start)', 0.0, 1e-6)}

    display_name = "Cont. Rectangle Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, _=None, x_size=1, y_size=1, direction=0,
                 x_start=None, y_start=None, z_start=None, delta_z=None):
        self.x_steps = int(x_size / spot_size)
        self.y_steps = int(y_size / spot_size)
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.delta_z = delta_z
        self.shot_count = self.x_steps
        self.frequency = frequency
        self._backwards = False
        self._steps = self.x_steps * self.y_steps

        self._curr_step = 0
        self._vx = math.cos(self.direction) * self.spot_size * self.frequency / shot_count
        self._vy = math.sin(self.direction) * self.spot_size * self.frequency / shot_count

        # v = math.sqrt(math.pow(self._vx, 2) + math.pow(self._vy, 2))

        self._dx = math.cos(self.direction) * self.spot_size * self.x_steps
        self._dy = math.sin(self.direction) * self.spot_size * self.y_steps
        # self._dz = dz

        # time = spot_size * spot_count / v
        # self._vz = dz / time

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, _, params):
        return cls(spot_size, shot_count, frequency, cleaning, params['x_size'].value, params['y_size'].value,
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

        if self._vx != 0:
            conn_mgr.stage.set_speed(self._vx, MCSAxis.X)
        if self._vy != 0:
            conn_mgr.stage.set_speed(self._vy, MCSAxis.Y)
        # if self._vz != 0:
        #    conn_mgr.stage.set_speed(self._vz, MCSAxis.Z)

    def next_move(self):
        if self._curr_step >= self.y_steps:
            return False

        self._curr_step += 1

        conn_mgr.trigger.go()

        if self._dx != 0:
            conn_mgr.stage.move(MCSAxis.X, self._dx, relative=True, wait=False)
        if self._dy != 0:
            conn_mgr.stage.move(MCSAxis.Y, self._dy, relative=True, wait=False)

        conn_mgr.stage.wait_until_status()

        line_dx = self.spot_size * math.sin(self.direction)
        line_dy = self.spot_size * math.cos(self.direction)

        conn_mgr.stage.move(MCSAxis.X, line_dx, relative=True, wait=False)
        conn_mgr.stage.move(MCSAxis.Y, line_dy, relative=True, wait=False)
        # conn_mgr.laser.single_shot()
        self._backwards = not self._backwards

        # if self._backwards:
        self._dx = -self._dx
        self._dy = -self._dy
        # try:
        #    conn_mgr.stage.move(MCSAxis.Z, self.delta_z[self._curr_step], relative=True, wait=False)
        # except ValueError:
        #    pass

        conn_mgr.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
