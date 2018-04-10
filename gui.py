import serial
import wx

from hardware.laser_compex import CompexLaserProtocol, OpMode
from hardware.mcs_stage import MCSStage, MCSAxis
from hardware.shutter import Shutter, AIODevice

DEBUG = True


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super(MainFrame, self).__init__(*args, **kwargs)

        self.init_ui()

    def init_ui(self):
        file_menu = wx.Menu()
        file_menu_close = file_menu.Append(wx.ID_EXIT, 'Quit', 'Quit application')

        menubar = wx.MenuBar()
        menubar.Append(file_menu, '&File')
        self.SetMenuBar(menubar)

        self.Bind(wx.EVT_MENU, self.on_quit, file_menu_close)

        p = wx.Panel(self)
        laser = LaserPanel(p)
        stage = StagePanel(p)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(laser, 0, wx.ALL, border=5)
        sizer.Add(stage, 0, wx.ALL, border=5)
        p.SetSizerAndFit(sizer)
        sizer.SetSizeHints(self)

    def on_quit(self, e):
        self.Close()


class LaserPanel(wx.Panel):
    def __init__(self, parent):
        super(LaserPanel, self).__init__(parent, wx.ID_ANY)

        ser_laser = serial.serial_for_url('/dev/ttyUSB1', timeout=1)
        self.laser_thread = serial.threaded.ReaderThread(ser_laser, CompexLaserProtocol)
        self.laser_thread.start()
        transport, self.laser = self.laser_thread.connect()
        self.shutter = Shutter(AIODevice(), 24)

        self.init_ui()

    def init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        btn_laser = wx.ToggleButton(self, label="Laser Off")

        btn_shutter = wx.ToggleButton(self, label="Shutter Closed")

        main_sizer.Add(btn_laser, 0, wx.ALL, border=5)
        main_sizer.Add(btn_shutter, 0, wx.ALL, border=5)

        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_laser, btn_laser)
        self.Bind(wx.EVT_TOGGLEBUTTON, self.on_toggle_shutter, btn_shutter)

        self.SetSizerAndFit(main_sizer)

    def on_toggle_laser(self, e):
        if e.EventObject.GetValue():
            self.laser.opmode = OpMode.ON
            e.EventObject.SetLabel("Laser On")
        else:
            self.laser.opmode = OpMode.OFF
            e.EventObject.SetLabel("Laser Off")

    def on_toggle_shutter(self, e):
        if e.EventObject.GetValue():
            self.shutter.set(True)
            e.EventObject.SetLabel("Shutter Open")
        else:
            self.shutter.set(False)
            e.EventObject.SetLabel("Shutter Closed")


class StagePanel(wx.Panel):
    def __init__(self, parent):
        super(StagePanel, self).__init__(parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.stage = MCSStage('usb:ix:0')
        if not DEBUG:
            self.stage.open_mcs()
            self.stage.find_references()
            self.stage.set_position_limit(MCSAxis.X, -25000000, 25000000)
            self.stage.set_position_limit(MCSAxis.Y, -34000000, 35400000)
            self.stage.set_position_limit(MCSAxis.Z, -750000, 2700000)

        self.speed_slider = wx.Slider(self, minValue=1, maxValue=17, style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        self.speed_map = [None] * 18
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
        stage_move_xp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        stage_move_xp.SetMinSize((40, 40))

        stage_move_xn = wx.Button(self)
        stage_move_xn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        stage_move_xn.SetMinSize((40, 40))

        stage_move_yp = wx.Button(self)
        stage_move_yp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_move_yp.SetMinSize((40, 40))

        stage_move_yn = wx.Button(self)
        stage_move_yn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_move_yn.SetMinSize((40, 40))

        stage_focus_cp = wx.Button(self)
        stage_focus_cp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_cp.SetMinSize((40, 40))

        stage_focus_cn = wx.Button(self)
        stage_focus_cn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_cn.SetMinSize((40, 40))

        stage_focus_fp = wx.Button(self)
        stage_focus_fp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_fp.SetMinSize((30, 40))

        stage_focus_fn = wx.Button(self)
        stage_focus_fn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_fn.SetMinSize((30, 40))

        self.speed_slider.SetMinSize((200, 51))
        self.speed_slider.SetToolTip("XY Speed")

        button_sizer = wx.GridBagSizer(0, 0)

        button_sizer.Add(stage_move_xp, (1, 2))
        button_sizer.Add(stage_move_xn, (1, 0))
        button_sizer.Add(stage_move_yp, (0, 1))
        button_sizer.Add(stage_move_yn, (2, 1))
        button_sizer.Add(stage_focus_cp, (0, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_cn, (2, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_fp, (0, 4), flag=wx.LEFT, border=2)
        button_sizer.Add(stage_focus_fn, (2, 4), flag=wx.LEFT, border=2)

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
        self.stage.move(axis, speed * direction, relative=True)

    def on_click_focus_c(self, e, direction):
        self.stage.move(MCSAxis.Z, 10000 * direction, relative=True)

    def on_click_focus_f(self, e, direction):
        self.stage.move(MCSAxis.Z, 100000 * direction, relative=True)


class GeolasPyApp(wx.App):
    def OnInit(self):
        frm = MainFrame(None, title="geolasPy", size=(700, 500))

        frm.Show()
        return True


if __name__ == '__main__':
    GeolasPyApp(False).MainLoop()
