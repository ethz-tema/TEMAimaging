import wx


class SettingsManager:
    pass


class PreferencesBaseDialog(wx.Dialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.notebook = wx.Notebook(self, wx.ID_ANY)

        self.btn_save = wx.Button(self, wx.ID_SAVE)
        self.btn_apply = wx.Button(self, wx.ID_APPLY)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_save.SetDefault()

        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply)

        self._init_ui()

    def _init_ui(self):
        self.SetTitle("Preferences")

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(self.notebook, 1, wx.ALL | wx.EXPAND, 5)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.AddButton(self.btn_save)
        btn_sizer.AddButton(self.btn_apply)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL | wx.EXPAND, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_save(self, e):
        pass

    def on_apply(self, e):
        pass


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
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "-25000000", min=-30000000, max=3000000), 0, 0, 0)
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "25000000", min=-30000000, max=30000000), 0, 0, 0)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Y"), 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "-34000000", min=-40000000, max=40000000), 0, 0, 0)
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "35400000", min=-40000000, max=40000000), 0, 0, 0)

        grid_sizer.Add(wx.StaticText(panel, wx.ID_ANY, "Z"), 0, wx.ALIGN_CENTER, 0)
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "-750000", min=-800000, max=3000000), 0, 0, 0)
        grid_sizer.Add(wx.SpinCtrl(panel, wx.ID_ANY, "2700000", min=-800000, max=3000000), 0, 0, 0)

        sizer.Add(grid_sizer, 1, wx.ALL | wx.EXPAND, 5)

        border.Add(sizer, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(border)
        self.notebook.AddPage(panel, "Stage")
