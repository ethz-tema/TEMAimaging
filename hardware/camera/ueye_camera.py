from threading import Thread

import numpy as np
from pyueye import ueye


class CameraException(Exception):
    def __init__(self, error_code):
        self.error_code = error_code

    def __str__(self):
        return 'ERR{:04d}'.format(self.error_code)


class Camera:
    @staticmethod
    def check_code(return_code, ok_codes=None):
        if ok_codes is None:
            ok_codes = [ueye.IS_SUCCESS]
        if return_code not in ok_codes:
            raise CameraException(return_code)
        return return_code

    @staticmethod
    def get_device_ids():
        camera_list = ueye.UEYE_CAMERA_LIST()
        Camera.check_code(ueye.is_GetCameraList(camera_list))
        return [int(cam_info.dwDeviceID) for cam_info in camera_list.uci]

    @staticmethod
    def get_bits_per_pixel(color_mode):
        return {
            ueye.IS_CM_SENSOR_RAW8: 8,
            ueye.IS_CM_SENSOR_RAW10: 16,
            ueye.IS_CM_SENSOR_RAW12: 16,
            ueye.IS_CM_SENSOR_RAW16: 16,
            ueye.IS_CM_MONO8: 8,
            ueye.IS_CM_RGB8_PACKED: 24,
            ueye.IS_CM_BGR8_PACKED: 24,
            ueye.IS_CM_RGBA8_PACKED: 32,
            ueye.IS_CM_BGRA8_PACKED: 32,
            ueye.IS_CM_BGR10_PACKED: 32,
            ueye.IS_CM_RGB10_PACKED: 32,
            ueye.IS_CM_BGRA12_UNPACKED: 64,
            ueye.IS_CM_BGR12_UNPACKED: 48,
            ueye.IS_CM_BGRY8_PACKED: 32,
            ueye.IS_CM_BGR565_PACKED: 16,
            ueye.IS_CM_BGR5_PACKED: 16,
            ueye.IS_CM_UYVY_PACKED: 16,
            ueye.IS_CM_UYVY_MONO_PACKED: 16,
            ueye.IS_CM_UYVY_BAYER_PACKED: 16,
            ueye.IS_CM_CBYCRY_PACKED: 16,
        }[color_mode]

    def __init__(self, dev_id, img_width=1280, img_height=1024, color_mode=ueye.IS_CM_RGB8_PACKED):
        self.h_cam = ueye.HIDS(dev_id)
        self.img_width = img_width
        self.img_height = img_height
        self.color_mode = color_mode
        self.aoi = ueye.IS_RECT()
        self.aoi.s32X = ueye.int(0)
        self.aoi.s32Y = ueye.int(0)
        self.aoi.s32Width = ueye.int(img_width)
        self.aoi.s32Height = ueye.int(img_height)
        self.bpp = Camera.get_bits_per_pixel(self.color_mode)
        self.n_channels = int((7 + self.bpp) / 8)

    def __enter__(self):
        self.init()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()

    def init(self):
        Camera.check_code(ueye.is_InitCamera(self.h_cam, None))
        Camera.check_code(ueye.is_SetColorMode(self.h_cam, self.color_mode))
        Camera.check_code(ueye.is_SetDisplayMode(self.h_cam, ueye.IS_SET_DM_DIB))
        Camera.check_code(ueye.is_AOI(self.h_cam, ueye.IS_AOI_IMAGE_SET_AOI, self.aoi, ueye.sizeof(self.aoi)))

    def freeze_video(self):
        mem_id = ueye.int()
        mem_ptr = ueye.c_mem_p()
        x = ueye.int()
        y = ueye.int()
        bits = ueye.int()
        pitch = ueye.int()
        Camera.check_code(ueye.is_AllocImageMem(self.h_cam, self.img_width, self.img_height, self.bpp, mem_ptr, mem_id))
        try:
            Camera.check_code(ueye.is_SetImageMem(self.h_cam, mem_ptr, mem_id))
            Camera.check_code(ueye.is_FreezeVideo(self.h_cam, ueye.IS_WAIT))
            Camera.check_code(ueye.is_InquireImageMem(self.h_cam, mem_ptr, mem_id, x, y, bits, pitch))
            raw_data = ueye.get_data(mem_ptr, x, y, bits, pitch, True)
            if self.n_channels == 1:
                return np.reshape(raw_data, (self.img_height, self.img_width)).copy()
            return np.reshape(raw_data, (self.img_height, self.img_width, self.n_channels)).copy()
        finally:
            ueye.is_FreeImageMem(self.h_cam, mem_ptr, mem_id)

    def exit(self):
        Camera.check_code(ueye.is_ExitCamera(self.h_cam))


class CameraThread(Thread):
    def __init__(self, camera, notify, timeout=100):
        super(CameraThread, self).__init__()
        self.alive = True
        self.camera = camera
        self.notify = notify
        self.timeout = timeout

    def run(self):
        while self.alive:
            # ignore image transfer errors
            try:
                image = self.camera.freeze_video()
                self.notify(self.camera, image)
            except CameraException as e:
                if e.error_code != ueye.IS_TRANSFER_ERROR:
                    raise e

    def stop(self):
        self.alive = False
        self.join()
