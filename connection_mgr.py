import serial
import wx
import wx.lib.pubsub.pub as pub

from hardware.laser_compex import CompexLaserProtocol
from hardware.mcs_stage import MCSStage, MCSAxis
from hardware.shutter import Shutter, AIODevice


class ConnectionManager:
    def __init__(self):
        self.laser = None
        self.laser_connected = False
        self._laser_thread = None

        self.trigger = None
        self.trigger_connected = False

        self.shutter = None
        self.shutter_connected = False
        self._shutter_device = None

        self.stage = None
        self.stage_connected = False

    def laser_connect(self):
        if not self.laser_connected:
            ser_laser = serial.serial_for_url('/dev/ttyUSB0', timeout=1)
            self._laser_thread = serial.threaded.ReaderThread(ser_laser, CompexLaserProtocol)
            self._laser_thread.protocol_factory.connection_lost = self.on_laser_connection_lost
            self._laser_thread.start()

            transport, self.laser = self._laser_thread.connect()

            self.laser_connected = True
            pub.sendMessage('laser.connection_changed', connected=True)

    def laser_disconnect(self):
        if self.laser_connected:
            self._laser_thread.stop()

            self.laser_connected = False
            pub.sendMessage('laser.connection_changed', connected=False)

    def on_laser_connection_lost(self, exc):
        self.laser_connected = False
        pub.sendMessage('laser.connection_changed', connected=False)
        pub.sendMessage('laser.lost_connection', exc=exc)

    def trigger_connect(self):
        if not self.trigger_connected:
            self.trigger_connected = True
            pub.sendMessage('trigger.connection_changed', connected=True)

    def trigger_disconnect(self):
        if self.trigger_connected:
            self.trigger_connected = False
            pub.sendMessage('trigger.connection_changed', connected=False)

    def shutter_connect(self):
        if not self.shutter_connected:
            self._shutter_device = AIODevice()
            try:
                self._shutter_device.connect()
            except:
                return
            self.shutter = Shutter(self._shutter_device, 24)

            self.shutter_connected = True
            pub.sendMessage('shutter.connection_changed', connected=True)

    def shutter_disconnect(self):
        if self.shutter_connected:
            self._shutter_device.disconnect()

            self.shutter_connected = False
            pub.sendMessage('shutter.connection_changed', connected=False)

    def stage_connect(self):
        if not self.stage_connected:
            self.stage = MCSStage('usb:ix:0')
            self.stage.open_mcs()

            self.stage.open_mcs()
            self.stage.find_references()
            self.stage.set_position_limit(MCSAxis.X, -25000000, 25000000)
            self.stage.set_position_limit(MCSAxis.Y, -34000000, 35400000)
            self.stage.set_position_limit(MCSAxis.Z, -750000, 2700000)

            self.stage_connected = True
            pub.sendMessage('stage.connection_changed', connected=True)

    def stage_disconnect(self):
        if self.stage_connected:
            self.stage.close_mcs()

            self.stage_connected = False
            pub.sendMessage('stage.connection_changed', connected=False)


conn_mgr = ConnectionManager()


class ConnectionManagerDialog(wx.Dialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.btn_laser_connect = wx.Button(self, wx.ID_ANY)
        self.btn_trigger_connect = wx.Button(self, wx.ID_ANY)
        self.btn_shutter_connect = wx.Button(self, wx.ID_ANY)
        self.btn_stage_connect = wx.Button(self, wx.ID_ANY)

        self.bmp_laser = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_trigger = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_shutter = wx.StaticBitmap(self, wx.ID_ANY)
        self.bmp_stage = wx.StaticBitmap(self, wx.ID_ANY)

        self.init_ui()
        self.Layout()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        grid_sizer = wx.GridSizer(4, 3, 5, 3)

        lbl_laser = wx.StaticText(self, wx.ID_ANY, "Laser:")

        if conn_mgr.laser_connected:
            self.bmp_laser.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_laser_connect.SetLabel("Disconnect")
        else:
            self.bmp_laser.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_laser_connect.SetLabel("Connect")

        grid_sizer.Add(lbl_laser, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        grid_sizer.Add(self.bmp_laser, 0, wx.ALIGN_CENTER | wx.ALL, 0)
        grid_sizer.Add(self.btn_laser_connect, 0, wx.ALIGN_CENTER | wx.ALL, 0)

        lbl_trigger = wx.StaticText(self, wx.ID_ANY, "Trigger:")

        if conn_mgr.trigger_connected:
            self.bmp_trigger.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_trigger_connect.SetLabel("Disconnect")
        else:
            self.bmp_trigger.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_trigger_connect.SetLabel("Connect")

        grid_sizer.Add(lbl_trigger, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.bmp_trigger, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.btn_trigger_connect, 0, wx.ALIGN_CENTER, 0)

        lbl_shutter = wx.StaticText(self, wx.ID_ANY, "Shutter:")

        if conn_mgr.shutter_connected:
            self.bmp_shutter.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_shutter_connect.SetLabel("Disconnect")
        else:
            self.bmp_shutter.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_shutter_connect.SetLabel("Connect")

        grid_sizer.Add(lbl_shutter, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.bmp_shutter, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.btn_shutter_connect, 0, wx.ALIGN_CENTER, 0)

        lbl_stage = wx.StaticText(self, wx.ID_ANY, "Stage:")

        if conn_mgr.stage_connected:
            self.bmp_stage.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_stage_connect.SetLabel("Disconnect")
        else:
            self.bmp_stage.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_stage_connect.SetLabel("Connect")

        grid_sizer.Add(lbl_stage, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.bmp_stage, 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(self.btn_stage_connect, 0, wx.ALIGN_CENTER, 0)

        self.Bind(wx.EVT_BUTTON, self.on_click_laser, self.btn_laser_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_trigger, self.btn_trigger_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_shutter, self.btn_shutter_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_stage, self.btn_stage_connect)

        pub.subscribe(self.on_connection_changed_laser, 'laser.connection_changed')
        pub.subscribe(self.on_connection_changed_trigger, 'trigger.connection_changed')
        pub.subscribe(self.on_connection_changed_shutter, 'shutter.connection_changed')
        pub.subscribe(self.on_connection_changed_stage, 'stage.connection_changed')

        sizer.Add(grid_sizer, 0, wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_click_laser(self, e):
        if conn_mgr.laser_connected:
            conn_mgr.laser_disconnect()
        else:
            conn_mgr.laser_connect()

    def on_click_trigger(self, e):
        if conn_mgr.trigger_connected:
            conn_mgr.trigger_disconnect()
        else:
            conn_mgr.trigger_connect()

    def on_click_shutter(self, e):
        if conn_mgr.shutter_connected:
            conn_mgr.shutter_disconnect()
        else:
            conn_mgr.shutter_connect()

    def on_click_stage(self, e):
        if conn_mgr.stage_connected:
            conn_mgr.stage_disconnect()
        else:
            conn_mgr.stage_connect()

    def on_connection_changed_laser(self, connected):
        if connected:
            self.bmp_laser.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_laser_connect.SetLabel("Disconnect")
        else:
            self.bmp_laser.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_laser_connect.SetLabel("Connect")

    def on_connection_changed_trigger(self, connected):
        if connected:
            self.bmp_trigger.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_trigger_connect.SetLabel("Disconnect")
        else:
            self.bmp_trigger.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_trigger_connect.SetLabel("Connect")

    def on_connection_changed_shutter(self, connected):
        if connected:
            self.bmp_shutter.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_shutter_connect.SetLabel("Disconnect")
        else:
            self.bmp_shutter.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_shutter_connect.SetLabel("Connect")

    def on_connection_changed_stage(self, connected):
        if connected:
            self.bmp_stage.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_TICK_MARK))
            self.btn_stage_connect.SetLabel("Disconnect")
        else:
            self.bmp_stage.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_CROSS_MARK))
            self.btn_stage_connect.SetLabel("Connect")
