import math

import arduino_trigger
import laser_compex
from mcs_stage import MCSAxis


class LineScan:
    def __init__(self, spot_size, spot_count, direction, shot_count=1, cleaning=False):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.shot_count = shot_count
        self.laser = None
        self.trigger = None
        self.stage = None
        self._skip_move = True
        self._cleaning = cleaning

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduTrigger
        self.trigger.set_count(self.shot_count)
        self.stage = stage

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
