import wx
import wx.dataview
from wx.lib.pubsub import pub

import core.scanner_registry
from core.conn_mgr import conn_mgr
from core.measurement import measurement_model, Step, MeasurementController
from core.utils import LaserStatusPoller, ShutterStatusPoller
from gui.dialogs import AddScanDialog
from gui.renderers import SequenceEditorTextRenderer, SequenceEditorToggleRenderer
from hardware.laser_compex import OpMode
from hardware.mcs_stage import MCSAxis


class MeasurementDVContextMenu(wx.Menu):
    def __init__(self, dvc, dv_item, *args, **kw):
        super().__init__(*args, **kw)

        self.dvc = dvc

        menu_item = self.Append(wx.ID_ADD, "Add step")
        self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_add(e, item), menu_item)

        if dv_item:
            menu_item = self.Append(wx.ID_DELETE, "Delete")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_delete(e, item), menu_item)

            menu_item = self.Append(wx.ID_ANY, "Set position")
            self.Bind(wx.EVT_MENU, lambda e, item=dv_item: self.on_click_set_position(e, item), menu_item)

    def on_click_add(self, e, item):
        dlg = AddScanDialog(self.dvc)
        if dlg.ShowModal() == wx.ID_ADD:
            scan_str = dlg.choice_scan_type.GetStringSelection()
            scan_type = core.scanner_registry.scanners_by_display_name[scan_str]
            if item:
                node = self.dvc.GetModel().ItemToObject(item)
                if isinstance(node, Step):
                    self.dvc.GetModel().insert_step(scan_type, node.index)
            else:
                self.dvc.GetModel().append_step(scan_type)

    def on_click_delete(self, e, item):
        node = self.dvc.GetModel().ItemToObject(item)
        if isinstance(node, Step):
            self.dvc.GetModel().delete_step(item)

    def on_click_set_position(self, e, item):
        # TODO: Implement
        print("on_click_set_position")


class MeasurementPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        super(MeasurementPanel, self).__init__(parent, wx.ID_ANY, *args, **kwargs)

        self.dvc = wx.dataview.DataViewCtrl(self,
                                            style=wx.BORDER_THEME | wx.dataview.DV_ROW_LINES | wx.dataview.DV_VERT_RULES | wx.dataview.DV_MULTIPLE)

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

        btn_add_step = wx.Button(self, wx.ID_ANY, label="Add Step")
        btn_sizer.Add(btn_add_step)

        sizer.Add(self.dvc, 1, wx.EXPAND)
        sizer.Add(btn_sizer, 0, wx.TOP | wx.ALIGN_RIGHT, border=5)

        self.Bind(wx.EVT_BUTTON, self.on_click_add_step, btn_add_step)
        self.dvc.Bind(wx.dataview.EVT_DATAVIEW_ITEM_CONTEXT_MENU, self.on_context_menu)
        self.dvc.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        self.SetSizerAndFit(sizer)

    def on_click_add_step(self, e):
        dlg = AddScanDialog(self)
        if dlg.ShowModal() == wx.ID_ADD:
            scan_str = dlg.choice_scan_type.GetStringSelection()
            scan_type = core.scanner_registry.scanners_by_display_name[scan_str]

            measurement_model.append_step(scan_type)

    def on_context_menu(self, e):
        item = e.GetItem()
        if item.IsOk():
            node = self.dvc.GetModel().ItemToObject(item)
            if isinstance(node, Step):
                self.PopupMenu(MeasurementDVContextMenu(self.dvc, item), e.GetPosition())
        else:
            self.PopupMenu(MeasurementDVContextMenu(self.dvc, None), e.GetPosition())

    def on_key_down(self, e):
        key = e.GetKeyCode()
        if key == wx.WXK_DELETE:
            if self.dvc.HasSelection():
                item = self.dvc.GetSelection()
                node = self.dvc.GetModel().ItemToObject(item)
                if isinstance(node, Step):
                    self.dvc.GetModel().delete_step(item)


class LaserPanel(wx.Panel):
    def __init__(self, parent):
        super(LaserPanel, self).__init__(parent, wx.ID_ANY)

        self.laser_poller = None
        self.shutter_poller = None

        pub.subscribe(self.on_laser_connection_changed, 'laser.connection_changed')
        pub.subscribe(self.on_laser_status_changed, 'laser.status_changed')

        pub.subscribe(self.on_shutter_connection_changed, 'shutter.connection_changed')
        pub.subscribe(self.on_shutter_status_changed, 'shutter.status_changed')

        self.laser_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Laser")
        self.btn_laser_off = wx.Button(self.laser_box.GetStaticBox(), label="Off")
        self.btn_laser_on = wx.Button(self.laser_box.GetStaticBox(), label="On")

        self.shutter_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Shutter")
        self.btn_shutter_open = wx.Button(self.shutter_box.GetStaticBox(), label="Open")

        self.init_ui()

    def init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.btn_laser_off.SetMinSize((40, 40))
        self.btn_laser_on.SetMinSize((40, 40))

        self.laser_box.Add(self.btn_laser_off, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.laser_box.Add(self.btn_laser_on, 0, wx.RIGHT, border=5)

        btn_shutter_close = wx.Button(self.shutter_box.GetStaticBox(), label="Close")
        btn_shutter_close.SetMinSize((40, 40))

        self.btn_shutter_open.SetMinSize((40, 40))

        self.shutter_box.Add(btn_shutter_close, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        self.shutter_box.Add(self.btn_shutter_open, 0, wx.RIGHT, border=5)

        main_sizer.Add(self.laser_box, 0, wx.BOTTOM, border=5)
        main_sizer.Add(self.shutter_box, 0, wx.ALL, border=0)

        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_off, self.btn_laser_off)
        self.Bind(wx.EVT_BUTTON, self.on_btn_laser_on, self.btn_laser_on)

        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_close, btn_shutter_close)
        self.Bind(wx.EVT_BUTTON, self.on_btn_shutter_open, self.btn_shutter_open)

        self.SetSizerAndFit(main_sizer)

    def on_btn_laser_off(self, e):
        conn_mgr.laser.opmode = OpMode.OFF

    def on_btn_laser_on(self, e):
        conn_mgr.laser.opmode = OpMode.ON

    def on_btn_shutter_close(self, e):
        conn_mgr.shutter.close()

    def on_btn_shutter_open(self, e):
        conn_mgr.shutter.open()

    def on_laser_connection_changed(self, connected):
        if connected:
            self.laser_poller = LaserStatusPoller(self, conn_mgr.laser)
            self.laser_poller.Start(700)
        else:
            self.laser_poller.Stop()

    def on_laser_status_changed(self, status):
        if status[0] == OpMode.ON:
            self.btn_laser_on.SetBackgroundColour((0, 255, 0))
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)
        elif status[0] == OpMode.OFF_WAIT:
            self.btn_laser_on.SetBackgroundColour((255, 255, 0))
        else:
            self.btn_laser_on.SetBackgroundColour(wx.NullColour)
            self.btn_laser_off.SetBackgroundColour(wx.NullColour)

    def on_shutter_connection_changed(self, connected):
        if connected:
            self.shutter_poller = ShutterStatusPoller(self, conn_mgr.shutter)
            self.shutter_poller.Start(1000)
        else:
            self.shutter_poller.Stop()

    def on_shutter_status_changed(self, status):
        if status:
            self.btn_shutter_open.SetBackgroundColour((0, 255, 0))
        else:
            self.btn_shutter_open.SetBackgroundColour(wx.NullColour)


class StagePanel(wx.Panel):
    def __init__(self, parent):
        super(StagePanel, self).__init__(parent, wx.ID_ANY, style=wx.SUNKEN_BORDER)

        self.speed_slider = wx.Slider(self, minValue=1, maxValue=17, style=wx.SL_HORIZONTAL | wx.SL_LABELS)

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
        stage_move_xp = wx.Button(self)
        stage_move_xp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_move_xp.SetMinSize((40, 40))

        stage_move_xn = wx.Button(self)
        stage_move_xn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_move_xn.SetMinSize((40, 40))

        stage_move_yp = wx.Button(self)
        stage_move_yp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))
        stage_move_yp.SetMinSize((40, 40))

        stage_move_yn = wx.Button(self)
        stage_move_yn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))
        stage_move_yn.SetMinSize((40, 40))

        stage_focus_cp = wx.Button(self)
        stage_focus_cp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_cp.SetMinSize((40, 40))

        stage_focus_cn = wx.Button(self)
        stage_focus_cn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_cn.SetMinSize((40, 40))

        stage_focus_fp = wx.Button(self)
        stage_focus_fp.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_DOWN))
        stage_focus_fp.SetMinSize((30, 40))

        stage_focus_fn = wx.Button(self)
        stage_focus_fn.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_GO_UP))
        stage_focus_fn.SetMinSize((30, 40))

        self.speed_slider.SetMinSize((200, 51))
        self.speed_slider.SetToolTip("XY Speed")
        self.speed_slider.SetValue(10)

        button_sizer = wx.GridBagSizer(0, 0)

        button_sizer.Add(stage_move_xp, (2, 1))
        button_sizer.Add(stage_move_xn, (0, 1))
        button_sizer.Add(stage_move_yp, (1, 0))
        button_sizer.Add(stage_move_yn, (1, 2))
        button_sizer.Add(stage_focus_cp, (2, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_cn, (0, 3), flag=wx.LEFT, border=10)
        button_sizer.Add(stage_focus_fp, (2, 4), flag=wx.LEFT, border=2)
        button_sizer.Add(stage_focus_fn, (0, 4), flag=wx.LEFT, border=2)

        button_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Focus", style=wx.ALIGN_CENTER), (1, 3), (1, 2),
                         wx.ALIGN_CENTER | wx.LEFT, border=10)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(button_sizer, 0, wx.ALL, 10)
        main_sizer.Add(self.speed_slider, 0, wx.ALL, 10)
        self.SetSizerAndFit(main_sizer)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=1: self.on_click_move(e, a, d), stage_move_xp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.X, d=-1: self.on_click_move(e, a, d), stage_move_xn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=1: self.on_click_move(e, a, d), stage_move_yp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Y, d=-1: self.on_click_move(e, a, d), stage_move_yn)

        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_c(e, d), stage_focus_cp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_c(e, d), stage_focus_cn)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=1: self.on_click_focus_f(e, d), stage_focus_fp)
        self.Bind(wx.EVT_BUTTON, lambda e, a=MCSAxis.Z, d=-1: self.on_click_focus_f(e, d), stage_focus_fn)

    def on_click_move(self, e, axis, direction):
        speed = self.speed_map[self.speed_slider.GetValue()]
        conn_mgr.stage.move(axis, speed * direction, relative=True)

    def on_click_focus_c(self, e, direction):
        conn_mgr.stage.move(MCSAxis.Z, 10000 * direction, relative=True)

    def on_click_focus_f(self, e, direction):
        conn_mgr.stage.move(MCSAxis.Z, 100000 * direction, relative=True)


class ScanCtrlPanel(wx.Panel):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.stop_event = None

        self.init_ui()

    def init_ui(self):
        scan_box = wx.StaticBoxSizer(wx.HORIZONTAL, self, label="Scan")

        btn_start_scan = wx.Button(self, wx.ID_ANY, 'Start')
        btn_stop_scan = wx.Button(self, wx.ID_ANY, 'Stop')

        scan_box.Add(btn_start_scan, 0, wx.LEFT | wx.BOTTOM | wx.RIGHT, border=5)
        scan_box.Add(btn_stop_scan, 0, wx.RIGHT, border=5)

        self.Bind(wx.EVT_BUTTON, self.on_click_start_scan, btn_start_scan)
        self.Bind(wx.EVT_BUTTON, self.on_click_stop_scan, btn_stop_scan)

        self.SetSizerAndFit(scan_box)

    def on_click_start_scan(self, e):
        meas_ctlr = MeasurementController(None, None, None)
        meas_ctlr.init_sequence(measurement_model.steps)

        self.stop_event = meas_ctlr.start_sequence()

    def on_click_stop_scan(self, e):
        if self.stop_event:
            self.stop_event.set()
