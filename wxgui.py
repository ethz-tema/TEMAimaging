import wx.dataview


class GeolasPyApp(wx.App):
    def OnInit(self):
        from gui.main_frame import MainFrame
        frm = MainFrame(None, title="geolasPy")

        frm.Show()
        return True


if __name__ == '__main__':
    GeolasPyApp(False).MainLoop()
