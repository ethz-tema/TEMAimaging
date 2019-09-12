import wx
from pubsub import pub

from gui.panels import CameraPanel


class CameraFrame(wx.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.camera_panel = CameraPanel(self, 720 * 2, 576 * 2)

        self.init_ui()

    def init_ui(self):
        sizer = wx.BoxSizer()
        sizer.Add(self.camera_panel)

        pub.subscribe(self.on_image_acquired, 'camera.image_acquired')
        self.SetSizerAndFit(sizer)

    def on_image_acquired(self, camera, image):
        wx.CallAfter(self.camera_panel.update_image, image)
