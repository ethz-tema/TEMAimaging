import logging
import time
from threading import Event
from typing import List

from PIL import Image, ImageOps

from core.conn_mgr import conn_mgr
from core.scanner_registry import ScannerMeta
from hardware.stage import AxisType, AxisMovementMode
from scans import Spot

logger = logging.getLogger(__name__)


class Engraver(metaclass=ScannerMeta):
    parameter_map = {'x_size': ('X Size', 0, 1000),
                     'y_size': ('Y Size', 0, 1000),
                     'x_start': ('X (Start)', 0.0, 1000),
                     'y_start': ('Y (Start)', 0.0, 1000),
                     'z_start': ('Z (Start)', 0.0, 1000),
                     'image_path': ('Image path', "", None),
                     'blank_spots': ('# of blank spots', 0, None)}

    display_name = "Engraver"

    def __init__(self, spot_size, shots_per_spot, frequency, image, cleaning=False, cleaning_delay=0, x_start=None,
                 y_start=None, z_start=None, blank_spots=0, x_size=0, y_size=0):
        self.x_size = x_size
        self.y_size = y_size
        self.spot_size = spot_size
        self.shots_per_spot = shots_per_spot
        self._dist_list = []
        self._curr_step = 0
        self._cleaning = cleaning
        self._cleaning_delay = cleaning_delay
        self.x_start = x_start
        self.y_start = y_start
        self.z_start = z_start
        self.frequency = frequency
        self.blank_spots = blank_spots
        self.blank_delay = 0

        self.coord_list = []  # type: List[Spot]

        flipped_image = ImageOps.flip(image)

        logger.info("Image pixel count: {}".format(len(list(flipped_image.getdata()))))

        def to_pixel_coords(index):
            x_pixels = flipped_image.size[0]

            x = index // x_pixels
            y = index % x_pixels
            return x, y

        i = 0
        black_pixel = 0
        for pixel in list(flipped_image.getdata()):
            if pixel == 0:
                x_pixel, y_pixel = to_pixel_coords(i)
                x_coord = round(x_start + (x_pixel * spot_size))
                y_coord = round(y_start + (y_pixel * spot_size))
                self.coord_list.append(Spot(x_coord, y_coord))
                conn_mgr.stage.movement_queue.put(
                    Spot(x_coord, y_coord))  # TODO: move this to init_scan since it modifies hardware state
                black_pixel += 1

            i += 1

        logger.info("Image black pixel count: {}".format(black_pixel))

        self.frame_event = Event()
        self.movement_completed_event = Event()

    @classmethod
    def from_params(cls, spot_size, shots_per_spot, frequency, cleaning, cleaning_delay, params):
        width = int(params['y_size'].value / spot_size)
        height = int(params['x_size'].value / spot_size)
        image = Image.open(params['image_path'].value).convert(mode='1').resize((width, height))
        return cls(spot_size, shots_per_spot, frequency, image, cleaning, cleaning_delay, params['x_start'].value,
                   params['y_start'].value, params['z_start'].value, params['blank_spots'].value,
                   params['x_size'].value, params['y_size'].value)

    @property
    def boundary_size(self):
        x = max(spot.X for spot in self.coord_list) - min(spot.X for spot in self.coord_list) + self.spot_size
        y = max(spot.Y for spot in self.coord_list) - min(spot.Y for spot in self.coord_list) + self.spot_size

        return x, y

    def init_scan(self, measurement):
        conn_mgr.stage.on_movement_completed += self.on_movement_completed

        self.blank_delay = measurement.blank_delay
        conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE

        conn_mgr.stage.on_frame_completed += self.on_frame_completed

        if self.z_start:
            conn_mgr.stage.axes[AxisType.Z].move(self.z_start)

        conn_mgr.trigger.set_count(self.shots_per_spot)
        conn_mgr.trigger.set_freq(self.frequency)
        conn_mgr.trigger.set_first_only(True)

        if self.z_start:
            self.movement_completed_event.wait()
            self.movement_completed_event.clear()

        conn_mgr.stage.on_movement_completed -= self.on_movement_completed

    def next_move(self):
        if self._curr_step >= len(self.coord_list):
            return False

        if self.blank_spots:
            time.sleep(self.blank_delay / 1000)
            conn_mgr.trigger.single_tof()
            self.blank_spots -= 1
            return True

        conn_mgr.stage.trigger_frame()

        self.frame_event.wait()
        self.frame_event.clear()

        conn_mgr.trigger.go_and_wait(self._cleaning, self._cleaning_delay)

        self._curr_step += 1
        return True

    def next_shot(self):
        pass

    def done(self):
        conn_mgr.stage.on_frame_completed -= self.on_frame_completed

    def on_frame_completed(self):
        self.frame_event.set()

    def on_movement_completed(self):
        self.movement_completed_event.set()
