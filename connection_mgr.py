import serial
import wx
import wx.lib.pubsub.pub as pub

from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import CompexLaserProtocol
from hardware.mcs_stage import MCSStage, MCSAxis
from hardware.shutter import Shutter, AIODevice, ShutterException


class ConnectionManager:
    def __init__(self):
        self.laser = None
        self.laser_connected = False
        self._laser_thread = None

        self.trigger = None
        self.trigger_connected = False
        self._trigger_thread = None

        self.shutter = None
        self.shutter_connected = False
        self._shutter_device = None

        self.stage = None
        self.stage_connected = False

    def laser_connect(self, port, rate):
        if not self.laser_connected:
            ser_laser = serial.serial_for_url(port, timeout=1, baudrate=rate)
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

    def trigger_connect(self, port, rate):
        if not self.trigger_connected:
            ser_trigger = serial.serial_for_url(port, timeout=1, baudrate=rate)
            self.trigger_thread = serial.threaded.ReaderThread(ser_trigger, ArduTrigger)
            self.trigger_thread.start()

            transport, self.trigger = self.trigger_thread.connect()

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

        # Laser
        self.stxt_laser_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_laser_port = wx.Choice(self, wx.ID_ANY, choices=["/dev/ttyUSB0", "/dev/ttyUSB1"])
        self.choice_laser_rate = wx.Choice(self, wx.ID_ANY, choices=["9600", "19200"])
        self.btn_laser_connect = wx.Button(self, wx.ID_ANY)

        # Trigger
        self.stxt_trigger_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_trigger_port = wx.Choice(self, wx.ID_ANY, choices=["/dev/ttyACM0", "/dev/ttyACM1"])
        self.choice_trigger_rate = wx.Choice(self, wx.ID_ANY, choices=["9600", "19200"])
        self.btn_trigger_connect = wx.Button(self, wx.ID_ANY)

        # Shutter
        self.stxt_shutter_status = wx.StaticText(self, wx.ID_ANY)
        self.num_shutter_output = wx.SpinCtrl(self, wx.ID_ANY, "24", min=1, max=32)
        self.btn_shutter_connect = wx.Button(self, wx.ID_ANY)

        # Stage
        self.stxt_stage_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_stage_port = wx.Choice(self, wx.ID_ANY, choices=["usb:ix:0"])
        self.btn_stage_connect = wx.Button(self, wx.ID_ANY)

        self.btn_close = wx.Button(self, wx.ID_ANY, "Close")

        self.init_ui()
        self.Layout()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_status_laser = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_trigger = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_shutter = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_stage = wx.StaticText(self, wx.ID_ANY, "Status:")

        lbl_port_laser = wx.StaticText(self, wx.ID_ANY, "Port:")
        lbl_port_trigger = wx.StaticText(self, wx.ID_ANY, "Port:")
        lbl_port_stage = wx.StaticText(self, wx.ID_ANY, "Port:")

        lbl_rate_laser = wx.StaticText(self, wx.ID_ANY, "Baud-Rate:")
        lbl_rate_trigger = wx.StaticText(self, wx.ID_ANY, "Baud-Rate:")

        # Laser
        laser_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Laser"), wx.VERTICAL)
        laser_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        laser_grid_sizer.Add(lbl_status_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.stxt_laser_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add((0, 0), 0, 0, 0)
        laser_grid_sizer.Add((0, 0), 0, 0, 0)
        laser_grid_sizer.Add(lbl_port_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.choice_laser_port, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(lbl_rate_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.choice_laser_rate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add((0, 0), 0, 0, 0)
        laser_grid_sizer.Add((0, 0), 0, 0, 0)
        laser_grid_sizer.Add((0, 0), 0, 0, 0)
        laser_grid_sizer.Add(self.btn_laser_connect, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, 0)

        laser_sizer.Add(laser_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(laser_sizer, 1, wx.ALL | wx.EXPAND, 5)

        # Trigger
        trigger_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Trigger"), wx.VERTICAL)
        trigger_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        trigger_grid_sizer.Add(lbl_status_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.stxt_trigger_status, 0, 0, 0)
        trigger_grid_sizer.Add((0, 0), 0, 0, 0)
        trigger_grid_sizer.Add((0, 0), 0, 0, 0)
        trigger_grid_sizer.Add(lbl_port_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.choice_trigger_port, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(lbl_rate_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.choice_trigger_rate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add((0, 0), 0, 0, 0)
        trigger_grid_sizer.Add((0, 0), 0, 0, 0)
        trigger_grid_sizer.Add((0, 0), 0, 0, 0)
        trigger_grid_sizer.Add(self.btn_trigger_connect, 0, 0, 0)

        trigger_sizer.Add(trigger_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(trigger_sizer, 1, wx.ALL | wx.EXPAND, 5)

        # Shutter
        shutter_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Shutter"), wx.VERTICAL)
        shutter_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        shutter_grid_sizer.Add(lbl_status_shutter, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add(self.stxt_shutter_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        lbl_output = wx.StaticText(self, wx.ID_ANY, "Output:")
        shutter_grid_sizer.Add(lbl_output, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add(self.num_shutter_output, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add((0, 0), 0, 0, 0)
        shutter_grid_sizer.Add(self.btn_shutter_connect, 0, wx.ALIGN_RIGHT, 0)
        shutter_grid_sizer.AddGrowableCol(2)

        shutter_sizer.Add(shutter_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(shutter_sizer, 1, wx.ALL | wx.EXPAND, 5)

        # Stage
        stage_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Stage"), wx.VERTICAL)
        stage_grid_sizer = wx.FlexGridSizer(0, 4, 5, 5)

        stage_grid_sizer.Add(lbl_status_stage, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        stage_grid_sizer.Add(self.stxt_stage_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add(lbl_port_stage, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        stage_grid_sizer.Add(self.choice_stage_port, 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add((0, 0), 0, 0, 0)
        stage_grid_sizer.Add(self.btn_stage_connect, 0, wx.ALIGN_RIGHT, 0)
        stage_grid_sizer.AddGrowableCol(2)

        stage_sizer.Add(stage_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(stage_sizer, 1, wx.ALL | wx.EXPAND, 5)

        sizer.Add(self.btn_close, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.LEFT | wx.RIGHT, 5)

        self.choice_laser_port.SetSelection(0)
        self.choice_laser_rate.SetSelection(0)

        self.choice_trigger_port.SetSelection(0)
        self.choice_trigger_rate.SetSelection(1)

        self.choice_stage_port.SetSelection(0)

        self.on_connection_changed_laser(conn_mgr.laser_connected)
        self.on_connection_changed_trigger(conn_mgr.trigger_connected)
        self.on_connection_changed_shutter(conn_mgr.shutter_connected)
        self.on_connection_changed_stage(conn_mgr.stage_connected)

        self.Bind(wx.EVT_BUTTON, self.on_click_laser, self.btn_laser_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_trigger, self.btn_trigger_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_shutter, self.btn_shutter_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_stage, self.btn_stage_connect)

        pub.subscribe(self.on_connection_changed_laser, 'laser.connection_changed')
        pub.subscribe(self.on_connection_changed_trigger, 'trigger.connection_changed')
        pub.subscribe(self.on_connection_changed_shutter, 'shutter.connection_changed')
        pub.subscribe(self.on_connection_changed_stage, 'stage.connection_changed')

        self.SetSizer(sizer)
        sizer.Fit(self)

    # noinspection PyUnusedLocal
    def on_click_laser(self, e):
        if conn_mgr.laser_connected:
            conn_mgr.laser_disconnect()
        else:
            conn_mgr.laser_connect(self.choice_laser_port.GetStringSelection(),
                                   self.choice_laser_rate.GetStringSelection())

    # noinspection PyUnusedLocal
    def on_click_trigger(self, e):
        if conn_mgr.trigger_connected:
            conn_mgr.trigger_disconnect()
        else:
            conn_mgr.trigger_connect(self.choice_trigger_port.GetStringSelection(),
                                     self.choice_trigger_rate.GetStringSelection())

    # noinspection PyUnusedLocal
    def on_click_shutter(self, e):
        if conn_mgr.shutter_connected:
            conn_mgr.shutter_disconnect()
        else:
            conn_mgr.shutter_connect(self.num_shutter_output.GetValue())

    # noinspection PyUnusedLocal
    def on_click_stage(self, e):
        if conn_mgr.stage_connected:
            conn_mgr.stage_disconnect()
        else:
            conn_mgr.stage_connect()

    def on_connection_changed_laser(self, connected):
        if connected:
            self.stxt_laser_status.SetLabel("Connected")
            self.stxt_laser_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_laser_connect.SetLabel("Disconnect")
        else:
            self.stxt_laser_status.SetLabel("Disconnected")
            self.stxt_laser_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_laser_connect.SetLabel("Connect")

    def on_connection_changed_trigger(self, connected):
        if connected:
            self.stxt_trigger_status.SetLabel("Connected")
            self.stxt_trigger_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_trigger_connect.SetLabel("Disconnect")
        else:
            self.stxt_trigger_status.SetLabel("Disconnected")
            self.stxt_trigger_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_trigger_connect.SetLabel("Connect")

    def on_connection_changed_shutter(self, connected):
        if connected:
            self.stxt_shutter_status.SetLabel("Connected")
            self.stxt_shutter_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_shutter_connect.SetLabel("Disconnect")
        else:
            self.stxt_shutter_status.SetLabel("Disconnected")
            self.stxt_shutter_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_shutter_connect.SetLabel("Connect")

    def on_connection_changed_stage(self, connected):
        if connected:
            self.stxt_stage_status.SetLabel("Connected")
            self.stxt_stage_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_stage_connect.SetLabel("Disconnect")
        else:
            self.stxt_stage_status.SetLabel("Disconnected")
            self.stxt_stage_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_stage_connect.SetLabel("Connect")
