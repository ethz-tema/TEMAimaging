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

from tema_imaging.core.settings import Settings


class PreferencesBaseDialog(wx.Dialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.ctrl_map = {}

        self.notebook = wx.Notebook(self, wx.ID_ANY)
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.btn_save = wx.Button(self, wx.ID_SAVE)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_save.SetDefault()

        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)

        self._init_ui()

    def _init_ui(self):
        self.SetTitle("Preferences")

        self.sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 12)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.AddButton(self.btn_save)
        btn_sizer.Realize()

        self.sizer.Add(btn_sizer, 0, wx.BOTTOM | wx.EXPAND, 12)

        self.SetSizer(self.sizer)
        self.sizer.Fit(self)

    def on_save(self, e):
        self._update_settings()
        Settings.save()
        self.EndModal(wx.ID_SAVE)

    def _update_settings(self):
        for key, ctrl in self.ctrl_map.items():
            if hasattr(ctrl, 'GetValue'):
                value = ctrl.GetValue()
            elif hasattr(ctrl, 'GetSelection'):
                value = ctrl.GetSelection()
            elif hasattr(ctrl, 'IsChecked'):
                value = ctrl.IsChecked()
            else:
                raise TypeError('No method found to get value from settings control')

            Settings.set(key, value)

        pub.sendMessage('settings.changed')


class PreferencesDialog(PreferencesBaseDialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self._create_stage_page()
        self._create_camera_page()

        self.sizer.Fit(self)

    def _create_stage_page(self):
        panel = wx.Panel(self.notebook, wx.ID_ANY)

        border = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.StaticBoxSizer(wx.StaticBox(panel, wx.ID_ANY, "General"),
                                  wx.HORIZONTAL)
        grid_sizer = wx.GridBagSizer(hgap=3, vgap=3)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Position polling rate (sec)"), pos=(0, 0), span=(1, 1),
                       flag=wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.SpinCtrlDouble(panel, wx.ID_ANY, max=5, initial=0.1, inc=0.1)
        ctrl.SetValue(Settings.get('stage.position_poll_rate'))
        self.ctrl_map['stage.position_poll_rate'] = ctrl
        grid_sizer.Add(ctrl, pos=(0, 1), span=(1, 1), flag=wx.ALIGN_RIGHT)
        grid_sizer.AddGrowableCol(0)

        sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 10)
        border.Add(sizer, 0, wx.ALL | wx.EXPAND, 10)

        sizer = wx.StaticBoxSizer(wx.StaticBox(panel, wx.ID_ANY, "Position Limits"),
                                  wx.HORIZONTAL)
        grid_sizer = wx.FlexGridSizer(4, 3, 5, 5)

        grid_sizer.Add((0, 0), 0, 0, 0)
        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Minimum"), 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Maximum"), 0, wx.ALIGN_CENTER, 0)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "X"), 0, wx.ALIGN_CENTER, 0)

        value = Settings.get('stage.pos_limit.X.min')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-30000000, max=3000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.X.min'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        value = Settings.get('stage.pos_limit.X.max')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-30000000, max=30000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.X.max'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Y"), 0, wx.ALIGN_CENTER, 0)

        value = Settings.get('stage.pos_limit.Y.min')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-40000000, max=40000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.Y.min'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        value = Settings.get('stage.pos_limit.Y.max')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-40000000, max=40000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.Y.max'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Z"), 0, wx.ALIGN_CENTER, 0)

        value = Settings.get('stage.pos_limit.Z.min')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-800000, max=3000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.Z.min'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        value = Settings.get('stage.pos_limit.Z.max')
        ctrl = wx.SpinCtrl(panel, wx.ID_ANY, min=-800000, max=3000000)
        ctrl.SetValue(value)
        self.ctrl_map['stage.pos_limit.Z.max'] = ctrl
        grid_sizer.Add(ctrl, 0, 0, 0)

        sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 10)
        border.Add(sizer, 0, wx.ALL | wx.EXPAND, 10)

        sizer = wx.StaticBoxSizer(wx.StaticBox(panel, wx.ID_ANY, "Referencing"),
                                  wx.HORIZONTAL)
        grid_sizer = wx.GridBagSizer(hgap=3, vgap=3)

        ctrl = wx.CheckBox(panel, wx.ID_ANY, 'Find position references when connection is established')
        ctrl.SetValue(Settings.get('stage.find_ref_on_connect'))
        self.ctrl_map['stage.find_ref_on_connect'] = ctrl
        grid_sizer.Add(ctrl, pos=(0, 0), span=(1, 2))

        ctrl = wx.CheckBox(panel, wx.ID_ANY, 'Reference X axis')
        ctrl.SetValue(Settings.get('stage.ref_x'))
        self.ctrl_map['stage.ref_x'] = ctrl
        grid_sizer.Add(ctrl, pos=(1, 0), span=(1, 2))

        ctrl = wx.CheckBox(panel, wx.ID_ANY, 'Reference Y axis')
        ctrl.SetValue(Settings.get('stage.ref_y'))
        self.ctrl_map['stage.ref_y'] = ctrl
        grid_sizer.Add(ctrl, pos=(2, 0), span=(1, 2))

        ctrl = wx.CheckBox(panel, wx.ID_ANY, 'Reference Z axis')
        ctrl.SetValue(Settings.get('stage.ref_z'))
        self.ctrl_map['stage.ref_z'] = ctrl
        grid_sizer.Add(ctrl, pos=(3, 0), span=(1, 2))

        sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 10)
        border.Add(sizer, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(border)
        self.notebook.AddPage(panel, "Stage")

    def _create_camera_page(self):
        panel = wx.Panel(self.notebook, wx.ID_ANY)

        border = wx.BoxSizer(wx.VERTICAL)

        sizer = wx.StaticBoxSizer(wx.StaticBox(panel, wx.ID_ANY, "General"),
                                  wx.HORIZONTAL)
        grid_sizer = wx.GridBagSizer(hgap=3, vgap=3)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Show feed in separate window"), pos=(0, 0), span=(1, 1),
                       flag=wx.ALIGN_CENTER_VERTICAL)
        ctrl = wx.CheckBox(panel, wx.ID_ANY)
        ctrl.SetValue(Settings.get('camera.separate_window'))
        self.ctrl_map['camera.separate_window'] = ctrl
        grid_sizer.Add(ctrl, pos=(0, 1), span=(1, 1), flag=wx.ALIGN_RIGHT)
        grid_sizer.AddGrowableCol(0)

        sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 10)
        border.Add(sizer, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(border)
        self.notebook.AddPage(panel, "Camera")
