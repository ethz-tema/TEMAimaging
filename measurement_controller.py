import math
from mcs_stage import MCSAxis, MCSStage
import laser_compex
import arduino_trigger


class LineScan:
    def __init__(self, spot_size, spot_count, direction, shot_count=1):
        self.spot_size = spot_size
        self.spot_count = spot_count
        self.direction = math.radians(direction)
        self.shot_count = shot_count
        self.laser = None
        self.trigger = None
        self.stage = None

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger # type: arduino_trigger.ArduinoTriggerProtocol
        self.trigger.set_count(self.shot_count)
        self.stage = stage

    def next_move(self):
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
            self.trigger.go_and_wait()
            return True
        return False


class Engraver:
    def __init__(self, spot_size, shot_count, image):
        self.spot_size = spot_size
        self.shot_count = shot_count
        self.image = image
        self._image_data = list(image.getdata())
        self.laser = None
        self.trigger = None
        self.stage = None
        self._curr_pos = [0, 0]

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger # type: arduino_trigger.ArduinoTriggerProtocol
        self.trigger.set_count(self.shot_count)
        self.stage = stage

    def next_move(self):
        if self._curr_pos[0] == self.image.size[0] and self._curr_pos[1] == self.image.size[1]:
            return False

        y = self.spot_size * 1e9
        x = 0
        if self._curr_pos[0] == self.image.size[0]:
            x = - self.spot_size * 1e9
            y = - self.image.size[0] * self.spot_size * 1e9
            self._curr_pos[0] = 0
            self._curr_pos[1] += 1
        else:
            self._curr_pos[0] += 1

        self.stage.move(MCSAxis.X, int(x), relative=True, wait=False)
        self.stage.move(MCSAxis.Y, int(y), relative=True, wait=False)
        self.stage.wait_until_status()
        return True

    def next_shot(self):
        if self._curr_pos[0] == self.image.size[0] and self._curr_pos[1] == self.image.size[1]:
            return False
        elif self._image_data[self._curr_pos[0] + self._curr_pos[1] * self.image.size[1]] == 0:
            self.trigger.go_and_wait()
            return True
        else:
            return True


class MeasurementController:
    def __init__(self, laser, trigger, stage):
        self.laser = laser # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduinoTriggerProtocol
        self.stage = stage  # type: MCSStage

    def start_scan(self, scan):
        scan.set_instruments(self.laser, self.trigger, self.stage)
        while scan.next_move():
            scan.next_shot()


