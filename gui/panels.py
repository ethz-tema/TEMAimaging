import wx
import wx.dataview
from wx.lib.pubsub import pub

import core.scanner_registry
from core.conn_mgr import conn_mgr
from core.measurement import measurement_model, Step, MeasurementController
from gui.dialogs import AddScanDialog
from gui.renderers import SequenceEditorTextRenderer, SequenceEditorToggleRenderer
from hardware.laser_compex import OpMode
from hardware.mcs_stage import MCSAxis


class MeasurementDVContextMenu(wx.Menu):
    def __init__(self, parent, dv_item, *args, **kw):
        super().__init__(*args, **kw)

        self.dvc = parent.dvc

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
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_go_to_start(e, item), menu_item)
            if not conn_mgr.stage_connected:
                menu_item.Enable(False)

            self.AppendSeparator()

            menu_item = self.Append(wx.ID_DELETE, "Delete", )
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

    def on_click_go_to_start(self, _, item):
        node = self.dvc.GetModel().ItemToObject(item)
        if isinstance(node, Step):
            conn_mgr.stage.move(MCSAxis.X, node.params['x_start'].value, wait=False)
            conn_mgr.stage.move(MCSAxis.Y, node.params['y_start'].value, wait=False)
            conn_mgr.stage.move(MCSAxis.Z, node.params['z_start'].value, wait=False)


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

        btn_sizer.Add(btn_sizer_left, 1)
        btn_sizer.Add(btn_sizer_right, 0)

        sizer.Add(self.dvc, 1, wx.EXPAND)
        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.TOP, border=5)

        btn_open_sequence.Bind(wx.EVT_BUTTON, self.on_click_open_sequence)
        btn_save_sequence.Bind(wx.EVT_BUTTON, self.on_click_save_sequence)
        self.Bind(wx.EVT_BUTTON, self.on_click_add_step, btn_add_step)
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
                node.params['x_start'].value = conn_mgr.stage.get_position(MCSAxis.X)
                node.params['y_start'].value = conn_mgr.stage.get_position(MCSAxis.Y)
                node.params['z_start'].value = conn_mgr.stage.get_position(MCSAxis.Z)
                self.dvc.GetModel().edit_step(node)

    def on_click_set_end_position(self, _, item):
        if item:
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                node.params['z_end'].value = conn_mgr.stage.get_position(MCSAxis.Z)
                self.dvc.GetModel().edit_step(node)

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


class LaserPanel(wx.Panel):
    def __init__(self, parent):
        super(LaserPanel, self).__init__(parent, wx.ID_ANY)

        self.btn_laser_off = wx.Button(self, label="Off")
        self.btn_laser_on = wx.Button(self, label="On")

        self.num_laser_voltage = wx.SpinCtrlDouble(self, size=(110, -1), min=22, max=30, inc=0.1)
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
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)
        elif status[0] == OpMode.OFF_WAIT:
            self.btn_laser_on.SetBackgroundColour((255, 255, 0))
        else:
            self.btn_laser_on.SetBackgroundColour(wx.NullColour)
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)

    def on_laser_hv_changed(self, hv):
        self.num_laser_voltage.SetValue(hv)

    def on_laser_egy_changed(self, egy):
        self.txt_laser_energy.SetValue(str(egy))

    def on_shutter_status_changed(self, status):
        if status:
            self.btn_shutter_open.SetBackgroundColour((0, 255, 0))
        else:
            self.btn_shutter_open.SetBackgroundColour(wx.NullColour)


class LaserManualShootPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, wx.ID_ANY, *args, **kw)

        self.btn_start_stop = wx.Button(self, label='Start')

        self.num_shots = wx.SpinCtrl(self, wx.ID_ANY, size=(130, -1), max=100000, initial=100)
        self.num_frequency = wx.SpinCtrl(self, wx.ID_ANY, size=(130, -1), max=100, initial=50)

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
            self.num_frequency.Enable()
            self.btn_start_stop.SetLabelText('Start')
        else:
            self.num_shots.Disable()
            self.num_frequency.Disable()
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

        self.speed_slider = wx.Slider(self, minValue=1, maxValue=17, style=wx.SL_HORIZONTAL | wx.SL_LABELS)

        self.txt_x_pos = wx.TextCtrl(self, size=(150, -1))
        self.txt_x_pos.Disable()
        self.txt_y_pos = wx.TextCtrl(self, size=(150, -1))
        self.txt_y_pos.Disable()
        self.txt_z_pos = wx.TextCtrl(self, size=(150, -1))
        self.txt_z_pos.Disable()

        self.stage_move_xp = wx.Button(self)
        self.stage_move_xn = wx.Button(self)
        self.stage_move_yp = wx.Button(self)
        self.stage_move_yn = wx.Button(self)
        self.stage_focus_cp = wx.Button(self)
        self.stage_focus_cn = wx.Button(self)
        self.stage_focus_fp = wx.Button(self)
        self.stage_focus_fn = wx.Button(self)

        self.speed_map = [1] * 18
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

        self.speed_slider.SetToolTip("XY Speed")
        self.speed_slider.SetValue(10)

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

        pos_sizer = wx.FlexGridSizer(3, 2, 5, 5)
        pos_sizer.Add(wx.StaticText(self, wx.ID_ANY, "X (nm): "), flag=wx.ALIGN_CENTER_VERTICAL)
        pos_sizer.Add(self.txt_x_pos)
        pos_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Y (nm): "), flag=wx.ALIGN_CENTER)
        pos_sizer.Add(self.txt_y_pos)
        pos_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Z (nm): "), flag=wx.ALIGN_CENTER_VERTICAL)
        pos_sizer.Add(self.txt_z_pos)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(button_sizer, 0, wx.ALL, 10)
        main_sizer.Add(self.speed_slider, 0, wx.ALL | wx.EXPAND, 10)
        main_sizer.Add(pos_sizer, 0, wx.ALL, 10)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=1: self.on_click_move(e, a, d), self.stage_move_xp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=-1: self.on_click_move(e, a, d), self.stage_move_xn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=1: self.on_click_move(e, a, d), self.stage_move_yp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=-1: self.on_click_move(e, a, d), self.stage_move_yn)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_c(e, d), self.stage_focus_cp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_c(e, d), self.stage_focus_cn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_f(e, d), self.stage_focus_fp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_f(e, d), self.stage_focus_fn)

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
            self.speed_slider.Disable()

        self.SetSizerAndFit(main_sizer)

    def on_click_move(self, _, axis, direction):
        speed = self.speed_map[self.speed_slider.GetValue()]
        conn_mgr.stage.move(axis, speed * direction * 1e-9, relative=True)

    @staticmethod
    def on_click_focus_c(_, direction):
        conn_mgr.stage.move(MCSAxis.Z, 100 * 1e-6 * direction, relative=True)

    @staticmethod
    def on_click_focus_f(_, direction):
        conn_mgr.stage.move(MCSAxis.Z, 10 * 1e-6 * direction, relative=True)

    def on_stage_position_changed(self, position):
        self.txt_x_pos.SetValue(str(position[0]))
        self.txt_y_pos.SetValue(str(position[1]))
        self.txt_z_pos.SetValue(str(position[2]))

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
            self.speed_slider.Enable()
        else:
            self.stage_move_xp.Disable()
            self.stage_move_xn.Disable()
            self.stage_move_yp.Disable()
            self.stage_move_yn.Disable()
            self.stage_focus_cp.Disable()
            self.stage_focus_cn.Disable()
            self.stage_focus_fp.Disable()
            self.stage_focus_fn.Disable()
            self.speed_slider.Disable()


class ScanCtrlPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.stop_event = None

        self.num_cleaning_shot_delay = wx.SpinCtrl(self, size=(115, -1), max=500, initial=200)
        self.num_step_delay = wx.SpinCtrl(self, size=(115, -1), max=5000, initial=0)

        self.num_cleaning_shot_delay.Bind(wx.EVT_SPINCTRL, self.on_num_cleaning_shot_delay_changed)

        pub.subscribe(self.on_model_loaded, 'measurement.model_loaded')

        self.init_ui()

    def init_ui(self):
        scan_box = wx.StaticBoxSizer(wx.VERTICAL, self, label="Scan")

        scan_grid = wx.GridBagSizer(5, 5)
        scan_btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        btn_start_scan = wx.Button(self, wx.ID_ANY, 'Start')
        btn_stop_scan = wx.Button(self, wx.ID_ANY, 'Stop')

        scan_grid.Add(wx.StaticText(self, label='CS Delay (ms):'), (0, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_cleaning_shot_delay, (0, 1))
        scan_grid.Add(wx.StaticText(self, label='Step Delay (ms):'), (1, 0), flag=wx.ALIGN_CENTER_VERTICAL)
        scan_grid.Add(self.num_step_delay, (1, 1))
        scan_btn_sizer.Add(btn_start_scan, 1, wx.RIGHT, 2.5)
        scan_btn_sizer.Add(btn_stop_scan, 1, wx.LEFT, 2.5)

        self.Bind(wx.EVT_BUTTON, self.on_click_start_scan, btn_start_scan)
        self.Bind(wx.EVT_BUTTON, self.on_click_stop_scan, btn_stop_scan)

        scan_box.Add(scan_grid, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)
        scan_box.Add(scan_btn_sizer, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT | wx.EXPAND, 5)
        self.SetSizerAndFit(scan_box)

    def on_num_cleaning_shot_delay_changed(self, _):
        measurement_model.measurement.cs_delay = self.num_cleaning_shot_delay.GetValue()

    def on_num_step_delay_changed(self, _):
        measurement_model.measurement.step_delay = self.num_step_delay.GetValue()

    def on_click_start_scan(self, _):
        meas_ctlr = MeasurementController(None, None, None)
        meas_ctlr.init_sequence(measurement_model.measurement)

        self.stop_event = meas_ctlr.start_sequence()

    def on_click_stop_scan(self, _):
        if self.stop_event:
            self.stop_event.set()

    def on_model_loaded(self):
        self.num_cleaning_shot_delay.SetValue(measurement_model.measurement.cs_delay)
