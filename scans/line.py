import math

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis


class LineScan(metaclass=ScannerMeta):
    parameter_map = {'spot_count': ('Spot Count', 1),
                     'direction': ('Direction', 0)}

    display_name = "Line Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, cleaning=False, spot_count=1, direction=0):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.shot_count = shot_count
        self.frequency = frequency
        self.laser = conn_mgr.laser
        self.trigger = conn_mgr.trigger
        self.stage = conn_mgr.stage
        self._skip_move = True
        self._cleaning = cleaning

        self.trigger.set_count(self.shot_count)
        self.trigger.set_freq(self.frequency)

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, params):
        return cls(spot_size, shot_count, frequency, cleaning, params['spot_count'].value, params['direction'].value)

    def next_move(self):
        if self._skip_move:
            self._skip_move = False
            return True
        if self.spot_count > 0:
            x = math.sin(self.direction) * self.spot_size * 1e9
            y = math.cos(self.direction) * self.spot_size * 1e9

            self.stage.move(MCSAxis.X, int(x), relative=True, wait=False)
            self.stage.move(MCSAxis.Y, int(y), relative=True, wait=False)
            self.stage.wait_until_status()
            self.spot_count -= 1
            return True
        return False

    def next_shot(self):
        if self.spot_count > 0:
            self.trigger.go_and_wait(self._cleaning)
            return True
        return False
