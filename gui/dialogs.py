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
import wx.adv

import core.scanner_registry
from core.conn_mgr import conn_mgr


class AddScanDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choice_scan_type = wx.Choice(self, wx.ID_ANY,
                                          choices=list(sorted(
                                              core.scanner_registry.scanners_by_display_name.keys())))  # TODO: use an OrderedDict here, so param order can be defined by devs
        self.btn_add = wx.Button(self, wx.ID_ADD, "")
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, "")

        self.init_ui()

    def init_ui(self):
        self.SetTitle("Add Scan")
        self.choice_scan_type.SetSelection(0)

        sizer = wx.BoxSizer(wx.VERTICAL)

        choice_sizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl_scan_type = wx.StaticText(self, wx.ID_ANY, "Scan Type:")
        choice_sizer.Add(lbl_scan_type, 0, wx.ALIGN_CENTER | wx.ALL, 5)
        choice_sizer.Add(self.choice_scan_type, 0, wx.ALIGN_CENTER | wx.RIGHT, 5)
        sizer.Add(choice_sizer, 1, wx.EXPAND, 0)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.Add(self.btn_cancel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        btn_sizer.Add(self.btn_add, 0, wx.ALIGN_CENTER_VERTICAL | wx.BOTTOM | wx.RIGHT | wx.TOP, 5)
        sizer.Add(btn_sizer, 1, wx.ALIGN_RIGHT, 0)

        self.Bind(wx.EVT_BUTTON, self.on_click_add, self.btn_add)

        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Layout()

    def on_click_add(self, e):
        self.EndModal(wx.ID_ADD)


class LaserStatusDialog(wx.Dialog):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.stxt_pressure = wx.StaticText(self)
        self.stxt_pressure.SetLabel("Pressure: {} mbar".format(conn_mgr.laser.pressure))
        self.stxt_filter_contamination = wx.StaticText(self)
        self.stxt_filter_contamination.SetLabel('Filter contamination: {}'.format(conn_mgr.laser.filter_contamination))

        self.stxt_interlock = wx.StaticText(self)
        self.stxt_interlock.SetLabel('Interlock: {}'.format(conn_mgr.laser.interlock))
        self.stxt_total_counter = wx.StaticText(self)
        self.stxt_total_counter.SetLabel('Total counter: {}'.format(conn_mgr.laser.total_counter))

        self.stxt_laser_type = wx.StaticText(self)
        self.stxt_laser_type.SetLabel('Type: {}'.format(conn_mgr.laser.laser_type))
        self.stxt_laser_version = wx.StaticText(self)
        self.stxt_laser_version.SetLabel('Version: {}'.format(conn_mgr.laser.version))

        self.stxt_laser_temp = wx.StaticText(self)
        temp = conn_mgr.laser.tube_temp
        self.stxt_laser_temp.SetLabel('Temperature:    {} °C'.format(temp))

        self.stxt_laser_temp_ctrl = wx.StaticText(self)
        self.stxt_laser_temp_ctrl.SetLabel('Temp. control: {}'.format(conn_mgr.laser.tube_temp_control))

        self.init_ui()

    def init_ui(self):
        self.SetTitle("Laser Status")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.stxt_pressure)
        sizer.Add(self.stxt_filter_contamination)
        sizer.Add(self.stxt_interlock)
        sizer.Add(self.stxt_total_counter)
        sizer.Add(self.stxt_laser_type)
        sizer.Add(self.stxt_laser_version)
        sizer.Add(self.stxt_laser_temp)
        sizer.Add(self.stxt_laser_temp_ctrl)

        self.SetSizerAndFit(sizer)


class AboutDialog:
    def __init__(self):
        self.init_ui()

    def init_ui(self):
        info = wx.adv.AboutDialogInfo()

        info.Name = "TEMAimaging"
        info.Icon = wx.Icon('logo.png')
        info.Copyright = "Copyright (c) 2020, ETH Zurich and others"
        info.Licence = """This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.
"""

        wx.adv.AboutBox(info)
