import logging

import serial
from pubsub import pub

from core import utils
from core.settings import Settings
from core.utils import LaserStatusPoller, ShutterStatusPoller
from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import CompexLaserProtocol
from hardware.shutter import AIODevice, ShutterException, Shutter
from hardware.stage import Stage
from hardware.stage.mcs_stage import MCSStage, MCSAxis
from hardware.ueye_camera import Camera, CameraException, CameraThread


class ConnectionManager:
    def __init__(self):
        self.laser = None
        self.laser_connected = False
        self._laser_thread = None
        self._laser_status_poller = None

        self.trigger = None
        self.trigger_connected = False
        self._trigger_thread = None

        self.shutter = None
        self.shutter_connected = False
        self._shutter_device = None
        self._shutter_status_poller = None

        self.stage = None  # type: Stage
        self.stage_connected = False
        self._stage_position_poller = None

        self.camera = None
        self.camera_connected = False
        self._camera_thread = None

        if Settings.get('general.connect_on_startup'):
            try:
                self.laser_connect(Settings.get('laser.conn.port'), Settings.get('laser.conn.rate'))
            except Exception as e:
                logging.exception(e)
            try:
                self.trigger_connect(Settings.get('trigger.conn.port'), Settings.get('trigger.conn.rate'))
            except Exception as e:
                logging.exception(e)
            try:
                self.shutter_connect(Settings.get('shutter.output'))
            except Exception as e:
                logging.exception(e)
            try:
                self.stage_connect(Settings.get('stage.conn.port'))
            except Exception as e:
                logging.exception(e)
            try:
                self.camera_connect(Settings.get('camera.conn.port'))
            except Exception as e:
                logging.exception(e)

    def laser_connect(self, port, rate):
        if not self.laser_connected:
            ser_laser = serial.serial_for_url(port, timeout=1, baudrate=rate)
            self._laser_thread = serial.threaded.ReaderThread(ser_laser, CompexLaserProtocol)
            self._laser_thread.protocol_factory.connection_lost = self.on_laser_connection_lost
            self._laser_thread.start()

            transport, self.laser = self._laser_thread.connect()

            self._laser_status_poller = LaserStatusPoller(self.laser)
            self._laser_status_poller.start()

            self.laser_connected = True
            pub.sendMessage('laser.connection_changed', connected=True)

    def laser_disconnect(self):
        if self.laser_connected:
            self._laser_status_poller.stop()
            self._laser_thread.stop()

            self.laser_connected = False
            pub.sendMessage('laser.connection_changed', connected=False)

    def on_laser_connection_lost(self, exc):
        self.laser_connected = False
        pub.sendMessage('laser.connection_changed', connected=False)
        pub.sendMessage('laser.lost_connection', exc=exc)

    def trigger_connect(self, port, rate):
        if not self.trigger_connected:
            ser_trigger = serial.serial_for_url(port, timeout=1, baudrate=rate)
            self._trigger_thread = serial.threaded.ReaderThread(ser_trigger, ArduTrigger)
            self._trigger_thread.start()

            transport, self.trigger = self._trigger_thread.connect()

            self.trigger_connected = True
            pub.sendMessage('trigger.connection_changed', connected=True)

    def trigger_disconnect(self):
        if self.trigger_connected:
            self._trigger_thread.stop()

            self.trigger_connected = False
            pub.sendMessage('trigger.connection_changed', connected=False)

    def shutter_connect(self, output):
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
            pub.sendMessage('shutter.connection_changed', connected=True)

    def shutter_disconnect(self):
        if self.shutter_connected:
            self._shutter_status_poller.stop()
            self._shutter_device.disconnect()

            self.shutter_connected = False
            pub.sendMessage('shutter.connection_changed', connected=False)

    def stage_connect(self, port):
        if not self.stage_connected:
            self.stage = MCSStage(port)
            self.stage.connect()

            if Settings.get('stage.find_ref_on_connect'):
                self.stage.find_references()

            self.stage.set_position_limit(MCSAxis.X, Settings.get('stage.pos_limit.X.min'),
                                          Settings.get('stage.pos_limit.X.max'))
            self.stage.set_position_limit(MCSAxis.Y, Settings.get('stage.pos_limit.Y.min'),
                                          Settings.get('stage.pos_limit.Y.max'))
            self.stage.set_position_limit(MCSAxis.Z, Settings.get('stage.pos_limit.Z.min'),
                                          Settings.get('stage.pos_limit.Z.max'))

            self.stage_connected = True
            pub.sendMessage('stage.connection_changed', connected=True)

            self._stage_position_poller = utils.StagePositionPoller(self.stage)
            self._stage_position_poller.start()

    def stage_disconnect(self):
        if self.stage_connected:
            self._stage_position_poller.stop()
            self.stage.disconnect()

            self.stage_connected = False
            pub.sendMessage('stage.connection_changed', connected=False)

    def camera_list(self):
        return ['CAM_ANY'] + ['CAM_{:03d}'.format(device_id) for device_id in Camera.get_device_ids()]

    def camera_connect(self, cam_id):
        if not self.camera_connected:
            dev_id = 0
            if cam_id != 'CAM_ANY':
                dev_id = int(cam_id[4:])
            self.camera = Camera(dev_id)
            try:
                self.camera.init()
            except CameraException:
                self.camera = None
                return
            self._camera_thread = CameraThread(self.camera, notify=ConnectionManager.camera_notify_image_acquired)
            self._camera_thread.start()
            self.camera_connected = True
            pub.sendMessage('camera.connection_changed', connected=True)

    @staticmethod
    def camera_notify_image_acquired(camera, image):
        pub.sendMessage('camera.image_acquired', camera=camera, image=image)

    def camera_disconnect(self):
        if self.camera_connected:
            self._camera_thread.stop()
            self._camera_thread = None
            try:
                self.camera.exit()
            except CameraException:
                return
            self.camera = None
            self.camera_connected = False
            pub.sendMessage('camera.connection_changed', connected=False)


conn_mgr = ConnectionManager()
