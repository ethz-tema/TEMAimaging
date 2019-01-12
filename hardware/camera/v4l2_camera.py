import glob

from PIL import Image
from PyV4L2Camera.camera import Camera as PYV4L2Camera

from hardware.camera import Camera, CameraException


class V4L2CameraException(CameraException):
    def __init__(self, fatal):
        super().__init__(fatal)


class V4L2Camera(Camera):
    driver_name = "v4l2"

    @staticmethod
    def get_device_ids():
        devices = glob.glob("/dev/video*")
        return devices

    def __init__(self, dev_id, img_width=640, img_height=480):
        super().__init__()
        self.camera = PYV4L2Camera(dev_id, img_width, img_height)
        self.img_width = img_width
        self.img_height = img_height

    def init(self):
        pass

    def get_frame(self):
        frame = self.camera.get_frame()
        return Image.frombytes('RGB', (self.img_width, self.img_height), frame, 'raw', 'RGB')

    def close(self):
        self.camera.close()
