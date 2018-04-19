import wx
import wx.lib.pubsub.pub as pub

from hardware.laser_compex import CompexLaserProtocol, OpMode
from hardware.mcs_stage import MCSAxis
from connection_mgr import conn_mgr, ConnectionManagerDialog
from settings_mgr import SettingsDialog

DEBUG = True


class LaserStatusChangedEvent(wx.PyCommandEvent):
    def __init__(self, evt_type, _id, status):
        super().__init__(evt_type, _id)

        self.status = status


class LaserStatusPoller(wx.Timer):
    def __init__(self, panel, laser, *args, **kw):
        super().__init__(*args, **kw)
        self._laser_panel = panel
        self._laser = laser  # type: CompexLaserProtocol

    def Notify(self):
        if DEBUG:
            pub.sendMessage('laser.status_changed', status=(OpMode.ON,))
        else:
            pub.sendMessage('laser.status_changed', status=self._laser.opmode)


class ShutterStatusPoller(wx.Timer):
    def __init__(self, panel, shutter, *args, **kw):
        super().__init__(*args, **kw)
        self._laser_panel = panel
        self._shutter = shutter

    def Notify(self):
            pub.sendMessage('shutter.status_changed', status=self._shutter.status)


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args, **kwargs)

        self.init_ui()

    def init_ui(self):
        file_menu = wx.Menu()
        file_menu_conn_mgr = file_menu.Append(wx.ID_ANY, 'Connection Manager', 'Open connection manager')
        file_menu_settings = file_menu.Append(wx.ID_PREFERENCES)
        file_menu.Append(wx.ID_SEPARATOR)
        file_menu_close = file_menu.Append(wx.ID_EXIT)

        menubar = wx.MenuBar()
        menubar.Append(file_menu, '&File')
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_connection_manager, file_menu_conn_mgr)
        self.Bind(wx.EVT_MENU, self.on_settings, file_menu_settings)
        self.Bind(wx.EVT_MENU, self.on_quit, file_menu_close)

        p = wx.Panel(self)
        laser = LaserPanel(p)
        stage = StagePanel(p)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(laser, 0, wx.ALL, border=5)
        sizer.Add(stage, 0, wx.ALL, border=5)
        p.SetSizerAndFit(sizer)
        sizer.SetSizeHints(self)

    def on_connection_manager(self, e):
        dlg = ConnectionManagerDialog(self)
        dlg.ShowModal()

    def on_settings(self, e):
        dlg = SettingsDialog(self)
        dlg.ShowModal()

    def on_quit(self, e):
        conn_mgr.laser_disconnect()
        conn_mgr.trigger_disconnect()
        conn_mgr.shutter_disconnect()
        conn_mgr.stage_disconnect()
        self.Close()


class LaserPanel(wx.Panel):
    def __init__(self, parent):
        super(LaserPanel, self).__init__(parent, wx.ID_ANY)

        self.laser_poller = None
        self.shutter_poller = None

        pub.subscribe(self.on_laser_connection_changed, 'laser.connection_changed')
        pub.subscribe(self.on_laser_status_changed, 'laser.status_changed')

        pub.subscribe(self.on_shutter_connection_changed, 'shutter.connection_changed')
        pub.subscribe(self.on_shutter_status_changed, 'shutter.status_changed')

        self.laser_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Laser")
        self.btn_laser_off = wx.Button(self.laser_box.GetStaticBox(), label="Off")
        self.btn_laser_on = wx.Button(self.laser_box.GetStaticBox(), label="On")

        self.shutter_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Shutter")
        self.btn_shutter_open = wx.Button(self.shutter_box.GetStaticBox(), label="Open")

        self.init_ui()

    def init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.btn_laser_off.SetMinSize((40, 40))
        self.btn_laser_on.SetMinSize((40, 40))

        self.laser_box.Add(self.btn_laser_off, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.laser_box.Add(self.btn_laser_on, 0, wx.RIGHT, border=5)

        btn_shutter_close = wx.Button(self.shutter_box.GetStaticBox(), label="Close")
        btn_shutter_close.SetMinSize((40, 40))

        self.btn_shutter_open.SetMinSize((40, 40))

        self.shutter_box.Add(btn_shutter_close, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.shutter_box.Add(self.btn_shutter_open, 0, wx.RIGHT, border=5)

        main_sizer.Add(self.laser_box, 0, wx.ALL, border=5)
        main_sizer.Add(self.shutter_box, 0, wx.ALL, border=5)

        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_off, self.btn_laser_off)
        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_on, self.btn_laser_on)

        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_close, btn_shutter_close)
        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_open, self.btn_shutter_open)

        self.SetSizerAndFit(main_sizer)

    def on_btn_laser_off(self, e):
        conn_mgr.laser.opmode = OpMode.OFF

    def on_btn_laser_on(self, e):
        conn_mgr.laser.opmode = OpMode.ON

    def on_btn_shutter_close(self, e):
        conn_mgr.shutter.close()

    def on_btn_shutter_open(self, e):
        conn_mgr.shutter.open()

    def on_laser_connection_changed(self, connected):
        if connected:
            self.laser_poller = LaserStatusPoller(self, conn_mgr.laser)
            self.laser_poller.Start(700)
        else:
            self.laser_poller.Stop()

    def on_laser_status_changed(self, status):
        if status[0] == OpMode.ON:
            self.btn_laser_on.SetBackgroundColour((0, 255, 0))
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)
        elif status[0] == OpMode.OFF_WAIT:
            self.btn_laser_on.SetBackgroundColour((255, 255, 0))
        else:
            self.btn_laser_on.SetBackgroundColour(wx.NullColour)
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)

    def on_shutter_connection_changed(self, connected):
        if connected:
            self.shutter_poller = ShutterStatusPoller(self, conn_mgr.shutter)
            self.shutter_poller.Start(1000)
        else:
            self.shutter_poller.Stop()

    def on_shutter_status_changed(self, status):
        if status:
            self.btn_shutter_open.SetBackgroundColour((0, 255, 0))
        else:
            self.btn_shutter_open.SetBackgroundColour(wx.NullColour)


class StagePanel(wx.Panel):
    def __init__(self, parent):
        super(StagePanel, self).__init__(parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.speed_slider = wx.Slider(self, minValue=1, maxValue=17, style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        self.speed_map = [1] * 18
        self.speed_map[1] = 1
        self.speed_map[2] = 200
        self.speed_map[3] = 500
        self.speed_map[4] = 700
        self.speed_map[5] = 1000
        self.speed_map[6] = 2000
        self.speed_map[7] = 5000
        self.speed_map[8] = 10000
        self.speed_map[9] = 20000
        self.speed_map[10] = 40000
        self.speed_map[11] = 100000
        self.speed_map[12] = 200000
        self.speed_map[13] = 400000
        self.speed_map[14] = 800000
        self.speed_map[15] = 1000000
        self.speed_map[16] = 2000000
        self.speed_map[17] = 4000000

        self.init_ui()

    def init_ui(self):
        stage_move_xp = wx.Button(self)
        stage_move_xp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_move_xp.SetMinSize((40, 40))

        stage_move_xn = wx.Button(self)
        stage_move_xn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_move_xn.SetMinSize((40, 40))

        stage_move_yp = wx.Button(self)
        stage_move_yp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        stage_move_yp.SetMinSize((40, 40))

        stage_move_yn = wx.Button(self)
        stage_move_yn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        stage_move_yn.SetMinSize((40, 40))

        stage_focus_cp = wx.Button(self)
        stage_focus_cp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_cp.SetMinSize((40, 40))

        stage_focus_cn = wx.Button(self)
        stage_focus_cn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_cn.SetMinSize((40, 40))

        stage_focus_fp = wx.Button(self)
        stage_focus_fp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_fp.SetMinSize((30, 40))

        stage_focus_fn = wx.Button(self)
        stage_focus_fn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_fn.SetMinSize((30, 40))

        self.speed_slider.SetMinSize((200, 51))
        self.speed_slider.SetToolTip("XY Speed")
        self.speed_slider.SetValue(10)

        button_sizer = wx.GridBagSizer(0, 0)

        button_sizer.Add(stage_move_xp, (2, 1))
        button_sizer.Add(stage_move_xn, (0, 1))
        button_sizer.Add(stage_move_yp, (1, 0))
        button_sizer.Add(stage_move_yn, (1, 2))
        button_sizer.Add(stage_focus_cp, (2, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_cn, (0, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_fp, (2, 4), flag=wx.LEFT, border=2)
        button_sizer.Add(stage_focus_fn, (0, 4), flag=wx.LEFT, border=2)

        button_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Focus", style=wx.ALIGN_CENTER), (1, 3), (1, 2),
                         wx.ALIGN_CENTER | wx.LEFT, border=10)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(button_sizer, 0, wx.ALL, 10)
        main_sizer.Add(self.speed_slider, 0, wx.ALL, 10)
        self.SetSizerAndFit(main_sizer)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=1: self.on_click_move(e, a, d), stage_move_xp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=-1: self.on_click_move(e, a, d), stage_move_xn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=1: self.on_click_move(e, a, d), stage_move_yp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=-1: self.on_click_move(e, a, d), stage_move_yn)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_c(e, d), stage_focus_cp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_c(e, d), stage_focus_cn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_f(e, d), stage_focus_fp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_f(e, d), stage_focus_fn)

    def on_click_move(self, e, axis, direction):
        speed = self.speed_map[self.speed_slider.GetValue()]
        conn_mgr.stage.move(axis, speed * direction, relative=True)

    def on_click_focus_c(self, e, direction):
        conn_mgr.stage.move(MCSAxis.Z, 10000 * direction, relative=True)

    def on_click_focus_f(self, e, direction):
        conn_mgr.stage.move(MCSAxis.Z, 100000 * direction, relative=True)


class GeolasPyApp(wx.App):
    def OnInit(self):
        frm = MainFrame(None, title="geolasPy", size=(700, 500))

        frm.Show()
        return True


if __name__ == '__main__':
    GeolasPyApp(False).MainLoop()
