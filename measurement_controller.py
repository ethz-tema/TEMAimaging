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
        self._skip_move = True

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduinoTriggerProtocol
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
            self.trigger.go_and_wait()
            return True
        return False


class RectangleScan:
    def __init__(self, x_size, y_size, spot_size, direction, shot_count=1):
        self.x_steps = int(x_size / spot_size)
        self.y_steps = int(y_size / spot_size)
        self.spot_size = spot_size
        self.direction = math.radians(direction)
        self.shot_count = shot_count
        self.laser = None
        self.trigger = None
        self.stage = None
        self._curr_step = 0
        self._backwards = False
        self._steps = self.x_steps * self.y_steps

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduinoTriggerProtocol
        self.trigger.set_count(self.shot_count)
        self.stage = stage

    def next_move(self):
        self.trigger.go_and_wait()

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


class Engraver:
    def __init__(self, spot_size, shot_count, image):
        self.spot_size = spot_size
        self.shot_count = shot_count
        self.image = image
        self._image_data = list(image.getdata())
        self.laser = None
        self.trigger = None
        self.stage = None
        self._dist_list = []
        self._curr_step = 0
        self.init_steps()

    def set_instruments(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduinoTriggerProtocol
        self.trigger.set_count(self.shot_count)
        self.stage = stage

    def init_steps(self):
        self.image.show()
        line = 0
        col = 0
        i = 0
        coord_matrix = [[0 for _ in range(self.image.size[0])] for _ in range(self.image.size[1])]
        for pixel in self._image_data:
            coord_matrix[line][col] = 1 if pixel == 255 else 0
            col += 1

            if (i + 1) % self.image.size[0] == 0:
                line += 1
                col = 0

            i += 1

        self._dist_list = []
        prev = (0, 0)
        for x in range(self.image.size[1]):
            for y in range(self.image.size[0]):
                if not coord_matrix[x][y]:
                    self._dist_list.append((x - prev[0], y - prev[1]))
                    prev = (x, y)

    def next_move(self):
        if self._curr_step >= len(self._dist_list):
            return False

        dx = self._dist_list[self._curr_step][0] * self.spot_size * 1e9
        dy = self._dist_list[self._curr_step][1] * self.spot_size * 1e9
        self.stage.move(MCSAxis.X, int(dx), relative=True, wait=False)
        self.stage.move(MCSAxis.Y, int(dy), relative=True, wait=False)
        axes_moved = []
        if dx != 0:
            axes_moved.append(MCSAxis.X)
        if dy != 0:
            axes_moved.append(MCSAxis.Y)
        self.stage.wait_until_status(axes_moved)

        self.trigger.go_and_wait()
        self._curr_step += 1

        return True

    def next_shot(self):
        pass


class MeasurementController:
    def __init__(self, laser, trigger, stage):
        self.laser = laser # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduinoTriggerProtocol
        self.stage = stage  # type: MCSStage

    def start_scan(self, scan):
        scan.set_instruments(self.laser, self.trigger, self.stage)
        while scan.next_move():
            scan.next_shot()


