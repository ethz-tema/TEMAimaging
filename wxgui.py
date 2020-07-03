import logging

import wx.dataview
import wx.lib.mixins.inspection as wit

DEBUG = False

logging.basicConfig(level=logging.DEBUG)


class TemaImagingApp(wx.App, wit.InspectionMixin):
    def OnInit(self):
        if DEBUG:
            self.Init()

        from gui.main_frame import MainFrame
        frm = MainFrame(None, title="TEMAimaging")

        frm.Show()
        return True


if __name__ == '__main__':
    TemaImagingApp(False).MainLoop()
