import math

from core.scanner_registry import ScannerMeta
from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import CompexLaserProtocol
from hardware.mcs_stage import MCSAxis


class RectangleScan(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0),
                     'y_size': ('Y Size', 0),
                     'direction': ('Direction', 0)}

    display_name = "Rectangle Scan"

    def __init__(self, spot_size, shot_count=1, frequency=1, cleaning=False, x_size=1, y_size=1, direction=0):
        self.x_steps = int(x_size / spot_size)
        self.y_steps = int(y_size / spot_size)
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.shot_count = shot_count
        self.frequency = frequency
        self.laser = None
        self.trigger = None
        self.stage = None
        self._curr_step = 0
        self._backwards = False
        self._steps = self.x_steps * self.y_steps
        self._cleaning = cleaning

    @classmethod
    def from_params(cls, spot_size, shot_count, frequency, cleaning, params):
        return cls(spot_size, shot_count, frequency, cleaning, params['x_size'].value, params['y_size'].value,
                   params['direction'].value)

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: CompexLaserProtocol
        self.trigger = trigger  # type: ArduTrigger
        self.trigger.set_count(self.shot_count)
        self.trigger.set_freq(self.frequency)
        self.stage = stage

    def next_move(self):
        self.trigger.go_and_wait(self._cleaning)

        if self._curr_step + 1 == self._steps:
            return False

        if (self._curr_step + 1) % self.x_steps == 0:  # EOL
            dx = self.spot_size * math.sin(self.direction) * 1e9
            dy = self.spot_size * math.cos(self.direction) * 1e9
            self.stage.move(MCSAxis.X, int(dx), relative=True, wait=False)
            self.stage.move(MCSAxis.Y, int(dy), relative=True, wait=False)
            self._backwards = not self._backwards
        else:
            dx = self.spot_size * math.cos(self.direction) * 1e9
            dy = - self.spot_size * math.sin(self.direction) * 1e9
            if self._backwards:
                dx = -dx
                dy = -dy

            self.stage.move(MCSAxis.X, int(dx), relative=True, wait=False)
            self.stage.move(MCSAxis.Y, int(dy), relative=True, wait=False)

        self._curr_step += 1
        self.stage.wait_until_status()

        return True

    def next_shot(self):
        pass
