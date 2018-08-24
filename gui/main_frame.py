import wx
from pubsub import pub

from core.conn_mgr import conn_mgr
from gui.conn_mgr import ConnectionManagerDialog
from gui.dialogs import LaserStatusDialog
from gui.panels import LaserPanel, StagePanel, LaserManualShootPanel, ScanCtrlPanel, MeasurementPanel
from gui.preferences import PreferencesDialog


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args, **kwargs)

        icon = wx.Icon('logo.png')
        self.SetIcon(icon)

        self.status_bar = self.CreateStatusBar(2)

        self.laser_menu_status = wx.MenuItem(id=wx.ID_ANY, text="Status", helpString="Laser status")

        self.stage_menu_reference = wx.MenuItem(id=wx.ID_ANY, text='Reference axes', helpString='Reference stage axes')
        self.stage_menu_reset_speed = wx.MenuItem(id=wx.ID_ANY, text='Reset speed', helpString='Reset axis speeds')

        self.init_ui()

    def init_ui(self):
        file_menu = wx.Menu()
        file_menu_conn_mgr = file_menu.Append(wx.ID_ANY, 'Connection Manager', 'Open connection manager')
        file_menu_settings = file_menu.Append(wx.ID_PREFERENCES)
        file_menu.Append(wx.ID_SEPARATOR)
        file_menu_close = file_menu.Append(wx.ID_EXIT)

        laser_menu = wx.Menu()
        laser_menu.Append(self.laser_menu_status)

        stage_menu = wx.Menu()
        stage_menu.Append(self.stage_menu_reference)
        stage_menu.Append(self.stage_menu_reset_speed)

        if not conn_mgr.laser_connected:
            self.laser_menu_status.Enable(False)

        if not conn_mgr.stage_connected:
            self.stage_menu_reference.Enable(False)
            self.stage_menu_reset_speed.Enable(False)

        menubar = wx.MenuBar()
        menubar.Append(file_menu, '&File')
        menubar.Append(laser_menu, '&Laser')
        menubar.Append(stage_menu, '&Stage')
        self.SetMenuBar(menubar)

        p = wx.Panel(self)
        laser = LaserPanel(p)
        stage = StagePanel(p)
        laser_manual = LaserManualShootPanel(p)
        scan = ScanCtrlPanel(p)
        measurement = MeasurementPanel(p)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(laser, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(stage, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(laser_manual, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(scan, 0, wx.ALL, border=0)

        sizer.Add(measurement, 1, wx.ALL | wx.EXPAND, border=10)
        sizer.Add(vert_sizer, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, border=10)

        self.Bind(wx.EVT_MENU, self.on_connection_manager, file_menu_conn_mgr)
        self.Bind(wx.EVT_MENU, self.on_settings, file_menu_settings)
        self.Bind(wx.EVT_MENU, self.on_quit, file_menu_close)
        self.Bind(wx.EVT_MENU, self.on_click_laser_menu_status, self.laser_menu_status)
        self.Bind(wx.EVT_MENU, self.on_click_stage_menu_reference, self.stage_menu_reference)
        self.Bind(wx.EVT_MENU, self.on_click_stage_menu_reset_speed, self.stage_menu_reset_speed)

        self.Bind(wx.EVT_CLOSE, self.on_quit)

        pub.subscribe(self.on_laser_status_changed, 'laser.status_changed')
        pub.subscribe(self.on_laser_connection_changed, 'laser.connection_changed')
        pub.subscribe(self.on_stage_connection_changed, 'stage.connection_changed')
        pub.subscribe(self.on_measurement_step_changed, 'measurement.step_changed')
        pub.subscribe(self.on_measurement_done, 'measurement.done')

        p.SetSizerAndFit(sizer)
        sizer.SetSizeHints(self)

    def on_stage_connection_changed(self, connected):
        if connected:
            self.stage_menu_reference.Enable(True)
            self.stage_menu_reset_speed.Enable(True)
        else:
            self.stage_menu_reference.Enable(False)
            self.stage_menu_reset_speed.Enable(False)

    def on_connection_manager(self, _):
        dlg = ConnectionManagerDialog(self)
        dlg.ShowModal()

    def on_settings(self, _):
        dlg = PreferencesDialog(self)
        dlg.ShowModal()

    def on_laser_status_changed(self, status):
        self.status_bar.SetStatusText('Laser status: ' + str(status), 0)

    def on_measurement_step_changed(self, current_step):
        self.status_bar.SetStatusText('Current step: {}'.format(current_step), 1)

    def on_measurement_done(self, duration):
        self.status_bar.SetStatusText('', 1)

    def on_laser_connection_changed(self, connected):
        if connected:
            self.laser_menu_status.Enable(True)
        else:
            self.laser_menu_status.Enable(False)

    def on_quit(self, _):
        conn_mgr.laser_disconnect()
        conn_mgr.trigger_disconnect()
        conn_mgr.shutter_disconnect()
        conn_mgr.stage_disconnect()
        self.Destroy()

    def on_click_laser_menu_status(self, _):
        dlg = LaserStatusDialog(self)
        dlg.ShowModal()

    @staticmethod
    def on_click_stage_menu_reference(_):
        conn_mgr.stage.find_references()

    @staticmethod
    def on_click_stage_menu_reset_speed(_):
        conn_mgr.stage.set_speed(0)
