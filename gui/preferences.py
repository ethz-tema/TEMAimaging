import wx
import wx.lib.pubsub.pub as pub

from core.settings import Settings


class PreferencesBaseDialog(wx.Dialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.ctrl_map = {}

        self.notebook = wx.Notebook(self, wx.ID_ANY)

        self.btn_save = wx.Button(self, wx.ID_SAVE)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_save.SetDefault()

        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)

        self._init_ui()

    def _init_ui(self):
        self.SetTitle("Preferences")

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 12)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.AddButton(self.btn_save)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.BOTTOM | wx.EXPAND, 12)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_save(self, e):
        self._update_settings()
        Settings.save()
        self.Close()

    def _update_settings(self):
        for key, ctrl in self.ctrl_map.items():
            if hasattr(ctrl, 'GetValue'):
                value = ctrl.GetValue()
            elif hasattr(ctrl, 'GetSelection'):
                value = ctrl.GetSelection()
            elif hasattr(ctrl, 'IsChecked'):
                value = ctrl.IsChecked
            else:
                raise TypeError('No method found to get value from settings control')

            Settings.set(key, value)

        pub.sendMessage('settings.changed')


class PreferencesDialog(PreferencesBaseDialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self._create_stage_page()

        self.SetMinSize(self.GetBestSize())
        self.SetMaxSize(self.GetBestSize())

    def _create_stage_page(self):
        panel = wx.Panel(self.notebook, wx.ID_ANY)

        border = wx.BoxSizer(wx.VERTICAL)

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

        panel.SetSizer(border)
        self.notebook.AddPage(panel, "Stage")
