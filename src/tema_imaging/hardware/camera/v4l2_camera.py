# This file is part of the TEMAimaging project.
# Copyright (c) 2020, ETH Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import glob

from PIL import Image

try:
    from PyV4L2Camera.camera import Camera as PYV4L2Camera
except ImportError:
    pass

from tema_imaging.hardware.camera import Camera, CameraException


class V4L2CameraException(CameraException):
    pass


class V4L2Camera(Camera):
    driver_name = "v4l2"

    @staticmethod
    def get_device_ids() -> list[str]:
        devices = glob.glob("/dev/video*")
        return devices

    def __init__(self, dev_id: str, img_width: int = 640, img_height: int = 480) -> None:
        super().__init__(dev_id, img_width=640, img_height=480)
        self.camera = PYV4L2Camera(dev_id, img_width, img_height)

    def init(self) -> None:
        pass

    def get_frame(self) -> Image.Image:
        frame = self.camera.get_frame()
        return Image.frombytes('RGB', (self.img_width, self.img_height), frame, 'raw', 'RGB')

    def close(self) -> None:
        self.camera.close()
