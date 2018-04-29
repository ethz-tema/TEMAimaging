import wx
import wx.dataview

from core.conn_mgr import conn_mgr
from gui.conn_mgr import ConnectionManagerDialog
from gui.panels import LaserPanel, StagePanel, ScanCtrlPanel, MeasurementPanel
from gui.preferences import PreferencesDialog


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

        self.Bind(wx.EVT_CLOSE, self.on_quit)

        p = wx.Panel(self)
        laser = LaserPanel(p)
        stage = StagePanel(p)
        scan = ScanCtrlPanel(p)
        measurement = MeasurementPanel(p)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(laser, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(stage, 0, wx.ALL, border=0)
        vert_sizer.Add(scan, 0, wx.ALL, border=0)

        sizer.Add(measurement, 0, wx.ALL, border=5)
        sizer.Add(vert_sizer, 0, wx.ALL, border=5)

        p.SetSizerAndFit(sizer)
        sizer.SetSizeHints(self)

    def on_connection_manager(self, e):
        dlg = ConnectionManagerDialog(self)
        dlg.ShowModal()

    def on_settings(self, e):
        dlg = PreferencesDialog(self)
        dlg.ShowModal()

    def on_quit(self, e):
        conn_mgr.laser_disconnect()
        conn_mgr.trigger_disconnect()
        conn_mgr.shutter_disconnect()
        conn_mgr.stage_disconnect()
        self.Destroy()


class GeolasPyApp(wx.App):
    def OnInit(self):
        frm = MainFrame(None, title="geolasPy", size=(700, 500))

        frm.Show()
        return True


if __name__ == '__main__':
    GeolasPyApp(False).MainLoop()
