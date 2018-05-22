import logging

from PIL import Image, ImageOps

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.mcs_stage import MCSAxis

logger = logging.getLogger(__name__)


class Engraver(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0, 1000),
                     'y_size': ('Y Size', 0, 1000),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'image_path': ('Image path', "", None)}

    display_name = "Engraver"

    def __init__(self, spot_size, shot_count, image, cleaning=False, cleaning_delay=0):
        self.spot_size = spot_size
        self.shot_count = shot_count
        self.image = image
        self._image_data = list(image.getdata())
        self.laser = conn_mgr.laser
        self.trigger = conn_mgr.trigger
        self.stage = conn_mgr.stage
        self._dist_list = []
        self._curr_step = 0
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self.init_steps()

        self.trigger.set_count(self.shot_count)

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

        dx = self._dist_list[self._curr_step][0] * self.spot_size
        dy = self._dist_list[self._curr_step][1] * self.spot_size
        self.stage.move(MCSAxis.X, dx, relative=True, wait=False)
        self.stage.move(MCSAxis.Y, dy, relative=True, wait=False)
        axes_moved = []
        if dx != 0:
            axes_moved.append(MCSAxis.X)
        if dy != 0:
            axes_moved.append(MCSAxis.Y)
        self.stage.wait_until_status(axes_moved)

        self.trigger.go_and_wait(self._cleaning, self._cleaning_delay)
        self._curr_step += 1

        return True

    def next_shot(self):
        pass
