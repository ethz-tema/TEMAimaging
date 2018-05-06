import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class LineScan(metaclass=ScannerMeta):
    parameter_map = {'spot_count': ('Spot Count', 1),
                     'direction': ('Direction', 0.0),
                     'z_start': ('Z (Start)', 0.0),
                     'z_end': ('Z (End)', 0.0)}

    display_name = "Line Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, cleaning=False, spot_count=1, direction=0, delta_z=None):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.delta_z = delta_z
        self.shot_count = shot_count
        self.frequency = frequency
        self.laser = conn_mgr.laser
        self.trigger = conn_mgr.trigger
        self.stage = conn_mgr.stage

        self._cleaning = cleaning
        self._curr_step = 0
        self._dx = math.sin(self.direction) * self.spot_size * 1e9
        self._dy = math.cos(self.direction) * self.spot_size * 1e9

        self.trigger.set_count(self.shot_count)
        self.trigger.set_freq(self.frequency)

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, params):
        spot_count = params['spot_count'].value
        if spot_count > 1:
            dz = (params['z_end'].value - params['z_start'].value) / (spot_count - 1)
            dz_list = [dz] * (spot_count - 1)
        else:
            dz_list = []

        return cls(spot_size, shot_count, frequency, cleaning, spot_count, params['direction'].value, dz_list)

    def next_move(self):
        if self._curr_step >= self.spot_count:
            return False

        self.trigger.go_and_wait(self._cleaning)

        if self._curr_step + 1 >= self.spot_count:  # skip move after last shot
            return False

        self.stage.move(MCSAxis.X, int(self._dx), relative=True, wait=False)
        self.stage.move(MCSAxis.Y, int(self._dy), relative=True, wait=False)
        try:
            self.stage.move(MCSAxis.Z, self.delta_z[self._curr_step], relative=True, wait=False)
        except ValueError:
            pass

        self._curr_step += 1
        self.stage.wait_until_status()
        return True

    def next_shot(self):
        pass
