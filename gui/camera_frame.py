# This file is part of the TEMAimaging project.
# Copyright (c) 2020, ETH Zurich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

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
