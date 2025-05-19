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

import logging

import wx.dataview
import wx.lib.mixins.inspection as wit

DEBUG = False

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)


class TemaImagingApp(wx.App, wit.InspectionMixin):
    def OnInit(self) -> bool:
        if DEBUG:
            self.Init()

        from tema_imaging.gui.main_frame import MainFrame

        frm = MainFrame("TEMAimaging")

        frm.Show()
        return True


def main() -> None:
    TemaImagingApp(False).MainLoop()


if __name__ == "__main__":
    main()
