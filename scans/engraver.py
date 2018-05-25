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

    def __init__(self, spot_size, shots_per_spot, frequency, image, cleaning=False, cleaning_delay=0, x_start=None,
                 y_start=None,
                 z_start=None):
        self.spot_size = spot_size
        self.shots_per_spot = shots_per_spot
        self.image = image
        self.laser = conn_mgr.laser
        self.trigger = conn_mgr.trigger
        self.stage = conn_mgr.stage
        self._dist_list = []
        self._curr_step = 0
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.frequency = frequency
        self.init_scan()

    @classmethod
    def from_params(cls, spot_size, shots_per_spot, frequency, cleaning, cleaning_delay, params):
        width = int(params['y_size'].value / spot_size)
        height = int(params['x_size'].value / spot_size)
        image = Image.open(params['image_path'].value).convert(mode='1').resize((width, height))
        return cls(spot_size, shots_per_spot, frequency, image, cleaning, cleaning_delay)

    def init_scan(self):
        if self.x_start:
            conn_mgr.stage.move(MCSAxis.X, self.x_start, wait=False)
        if self.y_start:
            conn_mgr.stage.move(MCSAxis.Y, self.y_start, wait=False)
        if self.z_start:
            conn_mgr.stage.move(MCSAxis.Z, self.z_start, wait=False)

        self.trigger.set_count(self.shots_per_spot)
        self.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        self.image.show()
        flipped_image = ImageOps.flip(self.image)
        line = 0
        col = 0
        i = 0
        coord_matrix = [[0 for _ in range(flipped_image.size[0])] for _ in range(flipped_image.size[1])]
        logger.info("Image pixel count: {}".format(len(list(flipped_image.getdata()))))
        black_pixel = 0
        for pixel in list(flipped_image.getdata()):
            coord_matrix[line][col] = 1 if pixel == 255 else 0
            if pixel == 0:
                black_pixel += 1
            col += 1

            if (i + 1) % flipped_image.size[0] == 0:
                line += 1
                col = 0

            i += 1

        logger.info("Image black pixel count: {}".format(black_pixel))
        self._dist_list = []
        prev = (0, 0)
        for x in range(flipped_image.size[1]):
            for y in range(flipped_image.size[0]):
                if not coord_matrix[x][y]:
                    self._dist_list.append((x - prev[0], y - prev[1]))
                    prev = (x, y)

        conn_mgr.stage.wait_until_status()

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
