# This file is part of the TEMAimaging project.
# Copyright (c) 2020, ETH Zurich
# Copyright (c) 2020, University of Zurich
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

from types import TracebackType

from PIL import Image
from pyueye import ueye

from tema_imaging.hardware.camera import Camera, CameraException


class UeyeCameraException(CameraException):
    def __init__(self, error_code) -> None:
        super().__init__(False if error_code != ueye.IS_TRANSFER_ERROR else True)
        self.error_code = error_code

    def __str__(self) -> str:
        return "ERR{:04d}".format(self.error_code)


class UeyeCamera(Camera):
    driver_name = "uEye"

    @staticmethod
    def check_code(return_code, ok_codes=None):
        if ok_codes is None:
            ok_codes = [ueye.IS_SUCCESS]
        if return_code not in ok_codes:
            raise UeyeCameraException(return_code)
        return return_code

    @staticmethod
    def get_device_ids() -> list[str]:
        camera_list = ueye.UEYE_CAMERA_LIST()
        UeyeCamera.check_code(ueye.is_GetCameraList(camera_list))
        return [str(cam_info.dwDeviceID) for cam_info in camera_list.uci]

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

    def __init__(
        self,
        dev_id: str,
        img_width: int = 1280,
        img_height: int = 1024,
        color_mode=ueye.IS_CM_RGB8_PACKED,
    ) -> None:
        super().__init__(dev_id, img_width, img_height)
        self.h_cam = ueye.HIDS(int(dev_id))
        self.color_mode = color_mode
        self.aoi = ueye.IS_RECT()
        self.aoi.s32X = ueye.int(0)
        self.aoi.s32Y = ueye.int(0)
        self.aoi.s32Width = ueye.int(self.img_width)
        self.aoi.s32Height = ueye.int(self.img_height)
        self.bpp = UeyeCamera.get_bits_per_pixel(self.color_mode)
        self.n_channels = int((7 + self.bpp) / 8)

        self.mem_id = ueye.int()
        self.mem_ptr = ueye.c_mem_p()
        self.x = ueye.int()
        self.y = ueye.int()
        self.bits = ueye.int()
        self.pitch = ueye.int()

    def __enter__(self) -> None:
        self.init()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    def init(self) -> None:
        UeyeCamera.check_code(ueye.is_InitCamera(self.h_cam, None))

        UeyeCamera.check_code(ueye.is_SetColorMode(self.h_cam, self.color_mode))
        UeyeCamera.check_code(ueye.is_SetDisplayMode(self.h_cam, ueye.IS_SET_DM_DIB))
        UeyeCamera.check_code(
            ueye.is_AOI(
                self.h_cam, ueye.IS_AOI_IMAGE_SET_AOI, self.aoi, ueye.sizeof(self.aoi)
            )
        )

        UeyeCamera.check_code(
            ueye.is_AllocImageMem(
                self.h_cam,
                self.img_width,
                self.img_height,
                self.bpp,
                self.mem_ptr,
                self.mem_id,
            )
        )
        UeyeCamera.check_code(
            ueye.is_SetImageMem(self.h_cam, self.mem_ptr, self.mem_id)
        )
        UeyeCamera.check_code(ueye.is_CaptureVideo(self.h_cam, ueye.IS_DONT_WAIT))
        UeyeCamera.check_code(
            ueye.is_InquireImageMem(
                self.h_cam,
                self.mem_ptr,
                self.mem_id,
                self.x,
                self.y,
                self.bits,
                self.pitch,
            )
        )

        ueye.is_EnableEvent(self.h_cam, ueye.IS_SET_EVENT_FRAME)

    def get_frame(self) -> Image.Image:
        if (
            ueye.is_WaitEvent(self.h_cam, ueye.IS_SET_EVENT_FRAME, 1000)
            == ueye.IS_SUCCESS
        ):
            raw_data = ueye.get_data(
                self.mem_ptr, self.x, self.y, self.bits, self.pitch, False
            )
            if self.n_channels == 1:
                return Image.frombytes(
                    "L", (self.img_width, self.img_height), raw_data, "raw", "L"
                )
            return Image.frombytes(
                "RGB", (self.img_width, self.img_height), raw_data, "raw", "RGB"
            )

    def close(self) -> None:
        ueye.is_DisableEvent(self.h_cam, ueye.IS_SET_EVENT_FRAME)
        ueye.is_FreeImageMem(self.h_cam, self.mem_ptr, self.mem_id)
        UeyeCamera.check_code(ueye.is_ExitCamera(self.h_cam))
