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

import matplotlib.backends.backend_wxagg
import matplotlib.cm
import matplotlib.collections
import matplotlib.colors
import matplotlib.figure
import matplotlib.patches
import wx
import wx.dataview
from PIL import Image
from pubsub import pub

import core.scanner_registry
from core.conn_mgr import conn_mgr
from core.measurement import measurement_model, Step, MeasurementController
from gui.dialogs import AddScanDialog
from gui.renderers import SequenceEditorTextRenderer, SequenceEditorToggleRenderer
from gui.utils import FloatValidator
from hardware.laser_compex import OpMode
from hardware.stage import AxisType, AxisMovementMode


class MeasurementDVContextMenu(wx.Menu):
    def __init__(self, parent, dv_item, *args, **kw):
        super().__init__(*args, **kw)

        self.dvc = parent.dvc  # type: wx.dataview.DataViewCtrl

        if dv_item:
            menu_item = self.Append(wx.ID_ANY, "&Set start position\tCtrl-S")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: parent.on_click_set_start_position(e, item), menu_item)
            if not conn_mgr.stage_connected:
                menu_item.Enable(False)

            menu_item = self.Append(wx.ID_ANY, "&Set end position (Z only)\tCtrl-E")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: parent.on_click_set_end_position(e, item), menu_item)
            if not conn_mgr.stage_connected:
                menu_item.Enable(False)

            menu_item = self.Append(wx.ID_ANY, "&Go to start position\tCtrl-G")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: parent.on_click_go_to_start(e, item), menu_item)
            if not conn_mgr.stage_connected:
                menu_item.Enable(False)

            self.AppendSeparator()

            if self.dvc.GetModel().ItemToObject(dv_item).index >= 1:
                menu_item = self.Append(wx.ID_ANY, "Align in X+")
                self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_align(e, item, 0), menu_item)
                menu_item = self.Append(wx.ID_ANY, "Align in X-")
                self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_align(e, item, 1), menu_item)
                menu_item = self.Append(wx.ID_ANY, "Align in Y+")
                self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_align(e, item, 2), menu_item)
                menu_item = self.Append(wx.ID_ANY, "Align in Y-")
                self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_align(e, item, 3), menu_item)

                self.AppendSeparator()

            menu_item = self.Append(wx.ID_DELETE, "Delete")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_delete(e, item), menu_item)

        menu_item = self.Append(wx.ID_ADD, "Add step")
        self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_add(e, item), menu_item)

    def on_click_add(self, _, item):
        dlg = AddScanDialog(self.dvc)
        if dlg.ShowModal() == wx.ID_ADD:
            scan_str = dlg.choice_scan_type.GetStringSelection()
            scan_type = core.scanner_registry.scanners_by_display_name[scan_str]
            if item:
                node = self.dvc.GetModel().ItemToObject(item)
                if isinstance(node, Step):
                    step_item = self.dvc.GetModel().insert_step(scan_type, node.index)
                    self.dvc.Expand(step_item)
            else:
                step_item = self.dvc.GetModel().append_step(scan_type)
                self.dvc.Expand(step_item)

    def on_click_delete(self, _, item):
        node = self.dvc.GetModel().ItemToObject(item)
        if isinstance(node, Step):
            self.dvc.GetModel().delete_step(item)

    def on_click_align(self, _, item, direction):
        index = self.dvc.GetModel().ItemToObject(item).index
        if index >= 1:
            prev_step = self.dvc.GetModel().measurement.steps[index - 1]

            prev_scan = prev_step.scan_type.from_params(prev_step.spot_size, prev_step.shots_per_spot,
                                                        prev_step.frequency,
                                                        prev_step.cleaning_shot,
                                                        0, prev_step.params)

            x, y = prev_scan.boundary_size
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                if direction == 0:
                    node.params['x_start'].value = prev_scan.x_start + x
                    node.params['y_start'].value = prev_scan.y_start
                    self.dvc.GetModel().edit_step(node)
                elif direction == 1:
                    node.params['x_start'].value = prev_scan.x_start - x
                    node.params['y_start'].value = prev_scan.y_start
                    self.dvc.GetModel().edit_step(node)
                elif direction == 2:
                    node.params['x_start'].value = prev_scan.x_start
                    node.params['y_start'].value = prev_scan.y_start + y
                    self.dvc.GetModel().edit_step(node)
                elif direction == 3:
                    node.params['x_start'].value = prev_scan.x_start
                    node.params['y_start'].value = prev_scan.y_start - y
                    self.dvc.GetModel().edit_step(node)


class MeasurementPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super(MeasurementPanel, self).__init__(parent, wx.ID_ANY, *args, **kwargs)

        self.dvc = wx.dataview.DataViewCtrl(self,
                                            style=wx.BORDER_THEME | wx.dataview.DV_ROW_LINES |
                                                  wx.dataview.DV_VERT_RULES | wx.dataview.DV_MULTIPLE)

        self.dvc.SetMinSize((800, 300))

        # self.model = MeasurementViewModel()

        self.dvc.AssociateModel(measurement_model)

        c0 = self.dvc.AppendTextColumn('Step', 0)
        c0.SetMinWidth(50)

        c1 = wx.dataview.DataViewColumn('Type', SequenceEditorTextRenderer(), 1)
        c1.SetMinWidth(100)
        self.dvc.AppendColumn(c1)

        c2 = wx.dataview.DataViewColumn('', SequenceEditorTextRenderer(), 2)
        c2.SetMinWidth(100)
        self.dvc.AppendColumn(c2)

        c3 = wx.dataview.DataViewColumn('', SequenceEditorTextRenderer(), 3)
        c3.SetMinWidth(100)
        self.dvc.AppendColumn(c3)

        c4 = wx.dataview.DataViewColumn('Spot Size', SequenceEditorTextRenderer(), 4)
        c4.SetMinWidth(70)
        self.dvc.AppendColumn(c4)

        c5 = wx.dataview.DataViewColumn('Frequency', SequenceEditorTextRenderer(), 5)
        c5.SetMinWidth(75)
        self.dvc.AppendColumn(c5)

        c6 = wx.dataview.DataViewColumn('Shots per Spot', SequenceEditorTextRenderer(), 6)
        c6.SetMinWidth(100)
        self.dvc.AppendColumn(c6)

        c7 = wx.dataview.DataViewColumn("Cleaning shot", SequenceEditorToggleRenderer(), 7)
        c7.SetMinWidth(50)
        self.dvc.AppendColumn(c7)

        self.plot_panel = SequencePlotPanel(self)

        self.init_ui()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer_left = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer_right = wx.BoxSizer(wx.HORIZONTAL)

        btn_open_sequence = wx.Button(self, wx.ID_OPEN)
        btn_sizer_left.Add(btn_open_sequence, 0)

        btn_save_sequence = wx.Button(self, wx.ID_SAVE)
        btn_sizer_left.Add(btn_save_sequence, 0, wx.LEFT, border=5)

        btn_add_step = wx.Button(self, wx.ID_ANY, label="Add Step")
        btn_sizer_right.Add(btn_add_step)

        btn_plot_sequence = wx.Button(self, wx.ID_ANY, label="Plot")
        btn_sizer_right.Add(btn_plot_sequence, 0, wx.LEFT, border=5)

        btn_sizer.Add(btn_sizer_left, 1)
        btn_sizer.Add(btn_sizer_right, 0)

        sizer.Add(self.plot_panel, 0, wx.EXPAND)
        sizer.Add(self.dvc, 1, wx.EXPAND | wx.TOP, border=5)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.TOP, border=5)

        btn_open_sequence.Bind(wx.EVT_BUTTON, self.on_click_open_sequence)
        btn_save_sequence.Bind(wx.EVT_BUTTON, self.on_click_save_sequence)
        btn_add_step.Bind(wx.EVT_BUTTON, self.on_click_add_step)
        btn_plot_sequence.Bind(wx.EVT_BUTTON, self.on_click_plot_sequence)
        self.dvc.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_context_menu)
        self.dvc.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.SetSizerAndFit(sizer)

    def on_click_open_sequence(self, _):
        with wx.FileDialog(self, "Open Sequence", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return

            path = fd.GetPath()
            try:
                with open(path, 'r') as file:
                    self.dvc.GetModel().load_model(file)
            except IOError:
                raise
            except ValueError:
                wx.MessageBox('The file you tried to load is invalid.', 'Invalid file', wx.OK | wx.ICON_ERROR)

    def on_click_save_sequence(self, _):
        with wx.FileDialog(self, "Save sequence", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT) as fd:
            if fd.ShowModal() == wx.ID_CANCEL:
                return

            path = fd.GetPath()
            try:
                with open(path, 'w') as file:
                    self.dvc.GetModel().dump_model(file)
            except IOError:
                raise

    def on_click_plot_sequence(self, _):
        self.plot_panel.plot(measurement_model.measurement.steps)

    def on_click_add_step(self, _):
        dlg = AddScanDialog(self)
        if dlg.ShowModal() == wx.ID_ADD:
            scan_str = dlg.choice_scan_type.GetStringSelection()
            scan_type = core.scanner_registry.scanners_by_display_name[scan_str]

            step_item = measurement_model.append_step(scan_type)
            self.dvc.Expand(step_item)

    def on_click_set_start_position(self, _, item):
        if item:
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                node.params['x_start'].value = float(conn_mgr.stage.axes[AxisType.X].position)
                node.params['y_start'].value = float(conn_mgr.stage.axes[AxisType.Y].position)
                node.params['z_start'].value = float(conn_mgr.stage.axes[AxisType.Z].position)
                self.dvc.GetModel().edit_step(node)

    def on_click_set_end_position(self, _, item):
        if item:
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                node.params['z_end'].value = float(conn_mgr.stage.axes[AxisType.Z].position)
                self.dvc.GetModel().edit_step(node)

    def on_click_go_to_start(self, _, item):
        node = self.dvc.GetModel().ItemToObject(item)
        if isinstance(node, Step):
            conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.X].move(node.params['x_start'].value)
            conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.Y].move(node.params['y_start'].value)
            conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.Z].move(node.params['z_start'].value)

    def on_context_menu(self, e):
        item = e.GetItem()
        if item.IsOk():
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                self.PopupMenu(MeasurementDVContextMenu(self, item), e.GetPosition())
        else:
            self.PopupMenu(MeasurementDVContextMenu(self, None), e.GetPosition())

    def on_key_down(self, e):
        key = e.GetKeyCode()
        ctrl = e.CmdDown()
        if key == wx.WXK_DELETE:
            if self.dvc.HasSelection():
                item = self.dvc.GetSelection()
                node = self.dvc.GetModel().ItemToObject(item)
                if isinstance(node, Step):
                    self.dvc.GetModel().delete_step(item)
        elif ctrl:
            if key == ord('E'):
                if self.dvc.HasSelection():
                    self.on_click_set_end_position(e, self.dvc.GetSelection())
            elif key == ord('S'):
                if self.dvc.HasSelection():
                    self.on_click_set_start_position(e, self.dvc.GetSelection())
            elif key == ord('G'):
                if self.dvc.HasSelection():
                    self.on_click_go_to_start(e, self.dvc.GetSelection())


class CameraPanel(wx.Panel):
    def __init__(self, parent, width=320, height=240):
        super().__init__(parent, wx.ID_ANY, size=wx.Size(width, height))
        self.width = width
        self.height = height
        self.static_bitmap = wx.Bitmap(width, height)
        self.image_set = False
        self.init_ui()

    def init_ui(self):
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)
        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, _):
        if self.image_set:
            dc = wx.AutoBufferedPaintDC(self)
            dc.DrawBitmap(self.static_bitmap, 0, 0)

    def update_image(self, im: Image):
        im = im.resize((self.width, self.height)).tobytes()

        self.static_bitmap.CopyFromBuffer(im)
        self.image_set = True
        self.Refresh()


class LaserPanel(wx.Panel):
    def __init__(self, parent):
        super(LaserPanel, self).__init__(parent, wx.ID_ANY)

        self.btn_laser_off = wx.Button(self, label="Off")
        self.btn_laser_on = wx.Button(self, label="On")

        self.num_laser_voltage = wx.SpinCtrlDouble(self, min=22, max=30, inc=0.1)
        self.txt_laser_energy = wx.TextCtrl(self, size=(110, -1))

        self.shutter_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Shutter")
        self.btn_shutter_close = wx.Button(self.shutter_box.GetStaticBox(), label="Close")
        self.btn_shutter_open = wx.Button(self.shutter_box.GetStaticBox(), label="Open")

        pub.subscribe(self.on_laser_connection_changed, 'laser.connection_changed')
        pub.subscribe(self.on_shutter_connection_changed, 'shutter.connection_changed')
        pub.subscribe(self.on_laser_status_changed, 'laser.status_changed')
        pub.subscribe(self.on_laser_hv_changed, 'laser.hv_changed')
        pub.subscribe(self.on_laser_egy_changed, 'laser.egy_changed')
        pub.subscribe(self.on_shutter_status_changed, 'shutter.status_changed')

        self.init_ui()

    def init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        laser_grid = wx.GridBagSizer(5, 5)

        self.btn_laser_off.SetMinSize((40, 40))
        self.btn_laser_on.SetMinSize((40, 40))

        laser_grid.Add(self.btn_laser_off, (0, 0), span=(2, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        laser_grid.Add(self.btn_laser_on, (0, 1), span=(2, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        laser_grid.Add(wx.StaticText(self, label="HV (kV):"), (0, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        laser_grid.Add(self.num_laser_voltage, (0, 3))
        laser_grid.Add(wx.StaticText(self, label="E (mJ):"), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL)
        laser_grid.Add(self.txt_laser_energy, (1, 3))

        self.btn_shutter_close.SetMinSize((40, 40))
        self.btn_shutter_open.SetMinSize((40, 40))

        self.shutter_box.Add(self.btn_shutter_close, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.shutter_box.Add(self.btn_shutter_open, 0, wx.RIGHT, border=5)

        laser_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Laser")
        laser_box.Add(laser_grid, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)
        main_sizer.Add(laser_box, 0, wx.BOTTOM, border=5)

        main_sizer.Add(self.shutter_box, 0, wx.ALL, border=0)

        self.num_laser_voltage.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_num_hv_changed)

        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_off, self.btn_laser_off)
        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_on, self.btn_laser_on)

        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_close, self.btn_shutter_close)
        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_open, self.btn_shutter_open)

        self.txt_laser_energy.Disable()

        if not conn_mgr.laser_connected:
            self.btn_laser_off.Disable()
            self.btn_laser_on.Disable()
            self.num_laser_voltage.Disable()

        if not conn_mgr.shutter_connected:
            self.btn_shutter_close.Disable()
            self.btn_shutter_open.Disable()

        self.SetSizerAndFit(main_sizer)

    @staticmethod
    def on_btn_laser_off(_):
        conn_mgr.laser.opmode = OpMode.OFF

    @staticmethod
    def on_btn_laser_on(_):
        conn_mgr.laser.opmode = OpMode.ON

    @staticmethod
    def on_btn_shutter_close(_):
        conn_mgr.shutter.close()

    @staticmethod
    def on_btn_shutter_open(_):
        conn_mgr.shutter.open()

    def on_num_hv_changed(self, _):
        conn_mgr.laser.hv = self.num_laser_voltage.GetValue()

    def on_laser_connection_changed(self, connected):
        if connected:
            self.btn_laser_off.Disable()
            self.btn_laser_on.Disable()
            self.num_laser_voltage.Enable()
        else:
            self.btn_laser_off.Disable()
            self.btn_laser_on.Disable()
            self.num_laser_voltage.Disable()

    def on_shutter_connection_changed(self, connected):
        if connected:
            self.btn_shutter_close.Enable()
            self.btn_shutter_open.Enable()
        else:
            self.btn_shutter_close.Disable()
            self.btn_shutter_open.Disable()

    def on_laser_status_changed(self, status):
        if status[0] == OpMode.ON:
            self.btn_laser_on.SetBackgroundColour((0, 255, 0))
            self.btn_laser_on.Disable()
            self.btn_laser_off.Enable()
        elif status[0] == OpMode.OFF_WAIT:
            self.btn_laser_on.SetBackgroundColour((255, 255, 0))
        else:
            self.btn_laser_on.SetBackgroundColour(wx.NullColour)
            self.btn_laser_on.Enable()
            self.btn_laser_off.Disable()

    def on_laser_hv_changed(self, hv):
        self.num_laser_voltage.SetValue(hv)

    def on_laser_egy_changed(self, egy):
        self.txt_laser_energy.SetValue(str(egy))

    def on_shutter_status_changed(self, open):
        if open:
            self.btn_shutter_open.SetBackgroundColour((0, 255, 0))
            self.btn_shutter_close.Enable()
        else:
            self.btn_shutter_open.SetBackgroundColour(wx.NullColour)

        self.btn_shutter_open.Enable(not open)
        self.btn_shutter_close.Enable(open)


class LaserManualShootPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, wx.ID_ANY, *args, **kw)

        self.btn_start_stop = wx.Button(self, label='Start')

        self.num_shots = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=100000, initial=100)
        self.num_frequency = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=100, initial=10)

        self.trigger_running = False

        self.init_ui()

    def init_ui(self):
        main_sizer = wx.StaticBoxSizer(wx.VERTICAL, self, label='Manual Laser Control')
        grid_sizer = wx.GridBagSizer(5, 5)

        grid_sizer.Add(wx.StaticText(self, wx.ID_ANY, 'Shots: '), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.num_shots, (0, 1))
        grid_sizer.Add(wx.StaticText(self, wx.ID_ANY, 'Frequency (Hz): '), (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        grid_sizer.Add(self.num_frequency, (1, 1))
        grid_sizer.Add(self.btn_start_stop, (2, 0), (1, 2), flag=wx.EXPAND)

        main_sizer.Add(grid_sizer, 0, wx.ALL, 5)

        self.btn_start_stop.Bind(wx.EVT_BUTTON, self.on_click_start_stop)
        self.num_frequency.Bind(wx.EVT_SPINCTRL, self.on_num_frequency_changed)

        pub.subscribe(self.on_trigger_connection_changed, 'trigger.connection_changed')
        pub.subscribe(self.on_trigger_done, 'trigger.done')

        if not conn_mgr.trigger_connected:
            self.num_shots.Disable()
            self.num_frequency.Disable()
            self.btn_start_stop.Disable()

        self.SetSizerAndFit(main_sizer)

    def toogle_ui(self, enable):
        if enable:
            self.num_shots.Enable()
            self.btn_start_stop.SetLabelText('Start')
        else:
            self.num_shots.Disable()
            self.btn_start_stop.SetLabelText('Stop')

    def on_click_start_stop(self, _):
        if self.trigger_running:
            conn_mgr.trigger.stop_trigger()
            self.trigger_running = False
            self.toogle_ui(True)
        else:
            conn_mgr.trigger.send_done_msg = True
            conn_mgr.trigger.set_freq(self.num_frequency.GetValue())
            conn_mgr.trigger.set_count(self.num_shots.GetValue())
            conn_mgr.trigger.go()
            self.trigger_running = True
            self.toogle_ui(False)

    def on_num_frequency_changed(self, _):
        if self.trigger_running:
            conn_mgr.trigger.set_freq(self.num_frequency.GetValue())

    def on_trigger_done(self):
        conn_mgr.trigger.send_done_msg = False
        self.trigger_running = False
        self.toogle_ui(True)

    def on_trigger_connection_changed(self, connected):
        if connected:
            self.num_shots.Enable()
            self.num_frequency.Enable()
            self.btn_start_stop.Enable()
        else:
            self.num_shots.Disable()
            self.num_frequency.Disable()
            self.btn_start_stop.Disable()


class StagePanel(wx.Panel):
    def __init__(self, parent):
        super(StagePanel, self).__init__(parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.num_step_size = wx.SpinCtrlDouble(self, min=0.1, max=1000, inc=0.1)

        self.txt_curr_x_pos = wx.StaticText(self)
        self.txt_curr_y_pos = wx.StaticText(self)
        self.txt_curr_z_pos = wx.StaticText(self)

        self.txt_x_pos = wx.TextCtrl(self, validator=FloatValidator())
        self.txt_y_pos = wx.TextCtrl(self, validator=FloatValidator())
        self.txt_z_pos = wx.TextCtrl(self, validator=FloatValidator())

        self.stage_move_xp = wx.Button(self)
        self.stage_move_xn = wx.Button(self)
        self.stage_move_yp = wx.Button(self)
        self.stage_move_yn = wx.Button(self)
        self.stage_focus_cp = wx.Button(self)
        self.stage_focus_cn = wx.Button(self)
        self.stage_focus_fp = wx.Button(self)
        self.stage_focus_fn = wx.Button(self)

        self.btn_stage_goto = wx.Button(self, wx.ID_ANY, "Go To")

        self.init_ui()

    def init_ui(self):
        self.stage_move_xp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        self.stage_move_xp.SetMinSize((40, 40))

        self.stage_move_xn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        self.stage_move_xn.SetMinSize((40, 40))

        self.stage_move_yp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        self.stage_move_yp.SetMinSize((40, 40))

        self.stage_move_yn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        self.stage_move_yn.SetMinSize((40, 40))

        self.stage_focus_cp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        self.stage_focus_cp.SetMinSize((40, 40))

        self.stage_focus_cn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        self.stage_focus_cn.SetMinSize((40, 40))

        self.stage_focus_fp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        self.stage_focus_fp.SetMinSize((30, 40))

        self.stage_focus_fn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        self.stage_focus_fn.SetMinSize((30, 40))

        self.num_step_size.SetToolTip("Step size (µm)")
        self.num_step_size.SetValue(10.0)

        button_sizer = wx.GridBagSizer(0, 0)

        button_sizer.Add(self.stage_move_xp, (2, 1))
        button_sizer.Add(self.stage_move_xn, (0, 1))
        button_sizer.Add(self.stage_move_yp, (1, 0))
        button_sizer.Add(self.stage_move_yn, (1, 2))
        button_sizer.Add(self.stage_focus_cp, (2, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(self.stage_focus_cn, (0, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(self.stage_focus_fp, (2, 4), flag=wx.LEFT, border=2)
        button_sizer.Add(self.stage_focus_fn, (0, 4), flag=wx.LEFT, border=2)

        button_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Focus", style=wx.ALIGN_CENTER), (1, 3), (1, 2),
                         wx.ALIGN_CENTER | wx.LEFT, border=10)

        pos_sizer = wx.FlexGridSizer(3, 3, 5, 5)
        s_txt = wx.StaticText(self, wx.ID_ANY, "X (µm)")
        s_txt.SetFont(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).Bold())
        pos_sizer.Add(s_txt)
        s_txt = wx.StaticText(self, wx.ID_ANY, "Y (µm)")
        s_txt.SetFont(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).Bold())
        pos_sizer.Add(s_txt)
        s_txt = wx.StaticText(self, wx.ID_ANY, "Z (µm)")
        s_txt.SetFont(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).Bold())
        pos_sizer.Add(s_txt)
        pos_sizer.Add(self.txt_curr_x_pos, flag=wx.ALIGN_CENTER_VERTICAL)
        pos_sizer.Add(self.txt_curr_y_pos, flag=wx.ALIGN_CENTER_VERTICAL)
        pos_sizer.Add(self.txt_curr_z_pos, flag=wx.ALIGN_CENTER_VERTICAL)
        pos_sizer.Add(self.txt_x_pos)
        pos_sizer.Add(self.txt_y_pos)
        pos_sizer.Add(self.txt_z_pos)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(button_sizer, 0, wx.ALL, 10)
        main_sizer.Add(self.num_step_size, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(pos_sizer, 0, wx.ALL, 10)
        main_sizer.Add(self.btn_stage_goto, 0, wx.ALL | wx.EXPAND, 10)

        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.X, d=1: self.on_click_move(e, a, d), self.stage_move_xp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.X, d=-1: self.on_click_move(e, a, d), self.stage_move_xn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Y, d=1: self.on_click_move(e, a, d), self.stage_move_yp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Y, d=-1: self.on_click_move(e, a, d), self.stage_move_yn)

        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Z, d=1: self.on_click_focus_c(e, d), self.stage_focus_cp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Z, d=-1: self.on_click_focus_c(e, d), self.stage_focus_cn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Z, d=1: self.on_click_focus_f(e, d), self.stage_focus_fp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=AxisType.Z, d=-1: self.on_click_focus_f(e, d), self.stage_focus_fn)

        self.Bind(wx.EVT_BUTTON, self.on_click_goto, self.btn_stage_goto)

        pub.subscribe(self.on_stage_position_changed, 'stage.position_changed')
        pub.subscribe(self.on_stage_connection_changed, 'stage.connection_changed')

        if not conn_mgr.stage_connected:
            self.stage_move_xp.Disable()
            self.stage_move_xn.Disable()
            self.stage_move_yp.Disable()
            self.stage_move_yn.Disable()
            self.stage_focus_cp.Disable()
            self.stage_focus_cn.Disable()
            self.stage_focus_fp.Disable()
            self.stage_focus_fn.Disable()
            self.num_step_size.Disable()
            self.txt_x_pos.Disable()
            self.txt_y_pos.Disable()
            self.txt_z_pos.Disable()
            self.btn_stage_goto.Disable()

        self.SetSizerAndFit(main_sizer)

    def on_click_move(self, _, axis, direction):
        step_size = self.num_step_size.GetValue() * 1000
        conn_mgr.stage.axes[axis].movement_mode = AxisMovementMode.CL_RELATIVE
        conn_mgr.stage.axes[axis].move(step_size * direction)

    def on_click_goto(self, _):
        try:
            conn_mgr.stage.axes[AxisType.X].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.X].move(float(self.txt_x_pos.GetValue()) * 1000)
        except ValueError:
            pass
        try:
            conn_mgr.stage.axes[AxisType.Y].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.Y].move(float(self.txt_y_pos.GetValue()) * 1000)
        except ValueError:
            pass
        try:
            conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_ABSOLUTE
            conn_mgr.stage.axes[AxisType.Z].move(float(self.txt_z_pos.GetValue()) * 1000)
        except ValueError:
            pass

    @staticmethod
    def on_click_focus_c(_, direction):
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_RELATIVE
        conn_mgr.stage.axes[AxisType.Z].move(100000 * direction)

    @staticmethod
    def on_click_focus_f(_, direction):
        conn_mgr.stage.axes[AxisType.Z].movement_mode = AxisMovementMode.CL_RELATIVE
        conn_mgr.stage.axes[AxisType.Z].move(10000 * direction)

    def on_stage_position_changed(self, position):
        self.txt_curr_x_pos.SetLabel(str(position[AxisType.X] / 1000))
        self.txt_curr_y_pos.SetLabel(str(position[AxisType.Y] / 1000))
        self.txt_curr_z_pos.SetLabel(str(position[AxisType.Z] / 1000))

    def on_stage_connection_changed(self, connected):
        if connected:
            self.stage_move_xp.Enable()
            self.stage_move_xn.Enable()
            self.stage_move_yp.Enable()
            self.stage_move_yn.Enable()
            self.stage_focus_cp.Enable()
            self.stage_focus_cn.Enable()
            self.stage_focus_fp.Enable()
            self.stage_focus_fn.Enable()
            self.num_step_size.Enable()
            self.txt_x_pos.Enable()
            self.txt_y_pos.Enable()
            self.txt_z_pos.Enable()
            self.btn_stage_goto.Enable()
        else:
            self.stage_move_xp.Disable()
            self.stage_move_xn.Disable()
            self.stage_move_yp.Disable()
            self.stage_move_yn.Disable()
            self.stage_focus_cp.Disable()
            self.stage_focus_cn.Disable()
            self.stage_focus_fp.Disable()
            self.stage_focus_fn.Disable()
            self.num_step_size.Disable()
            self.txt_x_pos.Disable()
            self.txt_y_pos.Disable()
            self.txt_z_pos.Disable()
            self.btn_stage_goto.Disable()


class ScanCtrlPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.meas_ctlr = MeasurementController()

        self.btn_start_scan = wx.Button(self, wx.ID_ANY, 'Start')
        self.btn_stop_scan = wx.Button(self, wx.ID_ANY, 'Stop')

        self.num_cleaning_shot_delay = wx.SpinCtrl(self, max=500, initial=200)
        self.num_shot_delay = wx.SpinCtrl(self, max=1000)
        self.num_step_delay = wx.SpinCtrl(self, max=5000)
        self.num_blank_delay = wx.SpinCtrl(self, max=5000)

        self.chk_step_trigger = wx.CheckBox(self, label="Use step trigger")

        self.num_cleaning_shot_delay.Bind(wx.EVT_SPINCTRL, self.on_num_cleaning_shot_delay_changed)
        self.num_shot_delay.Bind(wx.EVT_SPINCTRL, self.on_num_shot_delay_changed)
        self.num_step_delay.Bind(wx.EVT_SPINCTRL, self.on_num_step_delay_changed)
        self.num_blank_delay.Bind(wx.EVT_SPINCTRL, self.on_num_blank_delay_changed)
        self.chk_step_trigger.Bind(wx.EVT_CHECKBOX, self.on_chk_step_trigger_changed)

        pub.subscribe(self.on_model_loaded, 'measurement.model_loaded')
        pub.subscribe(self.on_measurement_done, 'measurement.done')

        self.init_ui()

        measurement_model.measurement.cs_delay = self.num_cleaning_shot_delay.GetValue()
        measurement_model.measurement.shot_delay = self.num_shot_delay.GetValue()
        measurement_model.measurement.step_delay = self.num_step_delay.GetValue()
        measurement_model.measurement.blank_delay = self.num_blank_delay.GetValue()
        measurement_model.measurement.step_trigger = self.chk_step_trigger.IsChecked()

    def init_ui(self):
        scan_box = wx.StaticBoxSizer(wx.VERTICAL, self, label="Scan")

        scan_grid = wx.GridBagSizer(5, 5)
        scan_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        scan_grid.Add(wx.StaticText(self, label='CS Delay (ms):'), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_cleaning_shot_delay, (0, 1))
        scan_grid.Add(wx.StaticText(self, label='Shot Delay (ms):'), (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_shot_delay, (1, 1))
        scan_grid.Add(wx.StaticText(self, label='Step Delay (ms):'), (2, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_step_delay, (2, 1))
        scan_grid.Add(wx.StaticText(self, label='Blank Delay (ms):'), (3, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_blank_delay, (3, 1))
        scan_grid.Add(self.chk_step_trigger, (4, 0))
        scan_btn_sizer.Add(self.btn_start_scan, 1, wx.RIGHT, 2)
        scan_btn_sizer.Add(self.btn_stop_scan, 1, wx.LEFT, 2)

        self.Bind(wx.EVT_BUTTON, self.on_click_start_scan, self.btn_start_scan)
        self.Bind(wx.EVT_BUTTON, self.on_click_stop_scan, self.btn_stop_scan)

        scan_box.Add(scan_grid, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)
        scan_box.Add(scan_btn_sizer, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT | wx.EXPAND, 5)

        self.btn_stop_scan.Disable()

        self.SetSizerAndFit(scan_box)

    def on_num_cleaning_shot_delay_changed(self, _):
        measurement_model.measurement.cs_delay = self.num_cleaning_shot_delay.GetValue()

    def on_num_shot_delay_changed(self, _):
        measurement_model.measurement.shot_delay = self.num_shot_delay.GetValue()

    def on_num_step_delay_changed(self, _):
        measurement_model.measurement.step_delay = self.num_step_delay.GetValue()

    def on_num_blank_delay_changed(self, _):
        measurement_model.measurement.blank_delay = self.num_blank_delay.GetValue()

    def on_chk_step_trigger_changed(self, _):
        measurement_model.measurement.step_trigger = self.chk_step_trigger.IsChecked()

    def on_click_start_scan(self, _):
        self.meas_ctlr.init_sequence(measurement_model.measurement)
        self.meas_ctlr.start_sequence()
        self.chk_step_trigger.Disable()
        self.num_cleaning_shot_delay.Disable()
        self.num_shot_delay.Disable()
        self.num_step_delay.Disable()
        self.num_blank_delay.Disable()
        self.btn_start_scan.Disable()
        self.btn_stop_scan.Enable()

    def on_click_stop_scan(self, _):
        self.meas_ctlr.stop()

    def on_model_loaded(self):
        self.num_cleaning_shot_delay.SetValue(measurement_model.measurement.cs_delay)
        self.num_shot_delay.SetValue(measurement_model.measurement.shot_delay)
        self.num_step_delay.SetValue(measurement_model.measurement.step_delay)
        self.num_blank_delay.SetValue(measurement_model.measurement.blank_delay)
        self.chk_step_trigger.SetValue(measurement_model.measurement.step_trigger)

    def on_measurement_done(self, duration):
        self.btn_start_scan.Enable()
        self.btn_stop_scan.Disable()
        self.chk_step_trigger.Enable()
        self.num_cleaning_shot_delay.Enable()
        self.num_shot_delay.Enable()
        self.num_step_delay.Enable()
        self.num_blank_delay.Enable()


class SequencePlotPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)
        self.figure = matplotlib.figure.Figure((2, 3))
        self.canvas = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(self, -1, self.figure)

        self.init_ui()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.canvas, 0, wx.EXPAND)
        self.SetSizerAndFit(sizer)

    def plot(self, steps):
        ax = self.figure.gca()
        ax.clear()
        sequence = []
        for step in steps:
            sequence.append(
                step.scan_type.from_params(step.spot_size, step.shots_per_spot, step.frequency, step.cleaning_shot,
                                           measurement_model.measurement.cs_delay, step.params))

        map = matplotlib.cm.get_cmap('gist_rainbow')
        map_norm = matplotlib.colors.Normalize(vmin=0, vmax=len(sequence))
        scalar_map = matplotlib.cm.ScalarMappable(norm=map_norm, cmap=map)

        i = 0
        legend_entries = []
        for step in sequence:
            size = [step.spot_size / 1000 for _ in step.coord_list]
            angle = [0 for _ in step.coord_list]
            offsets = [(spot.X / 1000, spot.Y / 1000) for spot in step.coord_list]
            ax.add_collection(matplotlib.collections.EllipseCollection(size, size, angle, offsets=offsets, units='x',
                                                                       transOffset=ax.transData,
                                                                       facecolors=scalar_map.to_rgba(i), alpha=0.5))

            legend_entries.append(matplotlib.patches.Circle([0, 0], color=scalar_map.to_rgba(i), alpha=0.5))

            i += 1

        ax.grid(True)
        ax.set_aspect('equal')
        ax.axis('scaled')
        ax.legend(legend_entries, range(len(sequence)), bbox_to_anchor=(1, 1))

        self.figure.tight_layout()
        self.canvas.draw()
