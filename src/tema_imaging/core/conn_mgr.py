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

import logging

import serial
import serial.threaded
from PIL import Image
from pubsub import pub

from tema_imaging.core import utils
from tema_imaging.core.settings import Settings
from tema_imaging.core.utils import LaserStatusPoller, ShutterStatusPoller
from tema_imaging.hardware.arduino_trigger import ArduTrigger
from tema_imaging.hardware.camera import (
    Camera,
    CameraException,
    CameraThread,
    camera_resolutions,
)
from tema_imaging.hardware.laser_compex import CompexLaserProtocol
from tema_imaging.hardware.shutter import AIODevice, Shutter, ShutterException
from tema_imaging.hardware.stage import AxisType, Stage
from tema_imaging.hardware.stage.mcs_stage import MCSStage


class ConnectionManager:
    def __init__(self) -> None:
        self.laser: CompexLaserProtocol | None = None
        self.laser_connected = False
        self._laser_thread: serial.threaded.ReaderThread[CompexLaserProtocol] | None = (
            None
        )
        self._laser_status_poller: LaserStatusPoller | None = None

        self.trigger: ArduTrigger | None = None
        self.trigger_connected = False
        self._trigger_thread: serial.threaded.ReaderThread[ArduTrigger] | None = None

        self.shutter: Shutter | None = None
        self.shutter_connected = False
        self._shutter_device: AIODevice | None = None
        self._shutter_status_poller: ShutterStatusPoller | None = None

        self.stage: Stage | None = None
        self.stage_connected = False
        self._stage_position_poller: utils.StagePositionPoller | None = None

        self.camera: Camera | None = None
        self.camera_connected = False
        self._camera_thread = None

        if Settings.get("general.connect_on_startup"):
            # try:
            #     self.laser_connect(
            #         Settings.get("laser.conn.port"), Settings.get("laser.conn.rate")
            #     )
            # except Exception as e:
            #     logging.exception(e)

            try:
                self.trigger_connect(
                    Settings.get("trigger.conn.port"), Settings.get("trigger.conn.rate")
                )
            except Exception as e:
                logging.exception(e)
            try:
                self.shutter_connect(Settings.get("shutter.output"))
            except Exception as e:
                logging.exception(e)
            try:
                self.stage_connect(Settings.get("stage.conn.port"))
            except Exception as e:
                logging.exception(e)
            try:
                self.camera_connect(
                    Settings.get("camera.driver"),
                    Settings.get("camera.conn.port"),
                    camera_resolutions[Settings.get("camera.resolution")],
                )
            except Exception as e:
                logging.exception(e)

    def laser_connect(self, port: str, rate: int) -> None:
        if not self.laser_connected:
            ser_laser = serial.serial_for_url(port, timeout=1, baudrate=rate)
            self._laser_thread = serial.threaded.ReaderThread(
                ser_laser, CompexLaserProtocol
            )
            self._laser_thread.protocol_factory.connection_lost = (
                self.on_laser_connection_lost
            )
            self._laser_thread.start()

            transport, self.laser = self._laser_thread.connect()

            assert self.laser is not None
            self._laser_status_poller = LaserStatusPoller(self.laser)
            self._laser_status_poller.start()

            self.laser_connected = True
            pub.sendMessage("laser.connection_changed", connected=True)

    def laser_disconnect(self) -> None:
        if self.laser_connected:
            self._laser_status_poller.stop()
            self._laser_thread.stop()

            self.laser_connected = False
            pub.sendMessage("laser.connection_changed", connected=False)

    def on_laser_connection_lost(self, exc: Exception) -> None:
        self.laser_connected = False
        pub.sendMessage("laser.connection_changed", connected=False)
        pub.sendMessage("laser.lost_connection", exc=exc)

    def trigger_connect(self, port: str, rate: int) -> None:
        if not self.trigger_connected:
            ser_trigger = serial.serial_for_url(port, timeout=1, baudrate=rate)
            self._trigger_thread = serial.threaded.ReaderThread(
                ser_trigger, ArduTrigger
            )
            self._trigger_thread.start()

            transport, self.trigger = self._trigger_thread.connect()

            self.trigger_connected = True
            pub.sendMessage("trigger.connection_changed", connected=True)

    def trigger_disconnect(self) -> None:
        if self.trigger_connected:
            self._trigger_thread.stop()

            self.trigger_connected = False
            pub.sendMessage("trigger.connection_changed", connected=False)

    def shutter_connect(self, output: int) -> None:
        if not self.shutter_connected:
            self._shutter_device = AIODevice()
            try:
                self._shutter_device.connect()
            except ShutterException:
                self._shutter_device.disconnect()
                return

            self.shutter = Shutter(self._shutter_device, output)

            self._shutter_status_poller = ShutterStatusPoller(self.shutter)
            self._shutter_status_poller.start()

            self.shutter_connected = True
            pub.sendMessage("shutter.connection_changed", connected=True)

    def shutter_disconnect(self) -> None:
        if self.shutter_connected:
            self._shutter_status_poller.stop()
            self._shutter_device.disconnect()

            self.shutter_connected = False
            pub.sendMessage("shutter.connection_changed", connected=False)

    def stage_connect(self, port: str) -> None:
        if not self.stage_connected:
            self.stage = MCSStage(port)
            self.stage.connect()

            if Settings.get("stage.find_ref_on_connect"):
                self.stage.find_references()

            self.stage.axes[AxisType.X].position_limit = (
                Settings.get("stage.pos_limit.X.min"),
                Settings.get("stage.pos_limit.X.max"),
            )
            self.stage.axes[AxisType.Y].position_limit = (
                Settings.get("stage.pos_limit.Y.min"),
                Settings.get("stage.pos_limit.Y.max"),
            )
            self.stage.axes[AxisType.Z].position_limit = (
                Settings.get("stage.pos_limit.Z.min"),
                Settings.get("stage.pos_limit.Z.max"),
            )

            self.stage_connected = True
            pub.sendMessage("stage.connection_changed", connected=True)

            self._stage_position_poller = utils.StagePositionPoller(self.stage)
            self._stage_position_poller.start()

    def stage_disconnect(self) -> None:
        if self.stage_connected:
            self._stage_position_poller.stop()
            self.stage.disconnect()

            self.stage_connected = False
            pub.sendMessage("stage.connection_changed", connected=False)

    def camera_list(self, driver_name: str) -> list[str]:
        driver = Camera.get_driver_from_name(driver_name)

        if driver:
            return driver.get_device_ids()
        else:
            return []

    def camera_connect(
        self, driver: str, dev_id: str, resolution: tuple[int, int]
    ) -> None:
        if not self.camera_connected:
            self.camera = Camera.get_driver_from_name(driver)(
                dev_id, resolution[0], resolution[1]
            )

            if self.camera:
                try:
                    self.camera.init()
                except CameraException:
                    self.camera = None
                    return
                self._camera_thread = CameraThread(
                    self.camera, notify=ConnectionManager.camera_notify_image_acquired
                )
                self._camera_thread.start()
                self.camera_connected = True
                pub.sendMessage("camera.connection_changed", connected=True)

    @staticmethod
    def camera_notify_image_acquired(camera: Camera, image: Image.Image) -> None:
        pub.sendMessage("camera.image_acquired", camera=camera, image=image)

    def camera_disconnect(self) -> None:
        if self.camera_connected:
            self._camera_thread.stop()
            self._camera_thread = None
            try:
                self.camera.close()
            except CameraException:
                return
            self.camera = None
            self.camera_connected = False
            pub.sendMessage("camera.connection_changed", connected=False)


conn_mgr = ConnectionManager()
