import wx


class SettingsManager:
    pass


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, *args, **kw):
        super().__init__(parent, *args, **kw)

        self.nb_settings = wx.Notebook(self, wx.ID_ANY)
        self.nb_settings_stage = wx.Panel(self.nb_settings, wx.ID_ANY)

        self.num_stage_x_min = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "-25000000", min=-30000000, max=3000000)
        self.num_stage_x_max = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "25000000", min=-30000000, max=30000000)
        self.num_stage_y_min = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "-34000000", min=-40000000, max=40000000)
        self.num_stage_y_max = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "35400000", min=-40000000, max=40000000)
        self.num_stage_z_min = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "-750000", min=-800000, max=3000000)
        self.num_stage_z_max = wx.SpinCtrl(self.nb_settings_stage, wx.ID_ANY, "2700000", min=-800000, max=3000000)

        self.btn_save = wx.Button(self, wx.ID_SAVE)
        self.btn_apply = wx.Button(self, wx.ID_APPLY)
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)
        self.btn_save.SetDefault()

        self.btn_save.Bind(wx.EVT_BUTTON, self.on_save)
        self.btn_apply.Bind(wx.EVT_BUTTON, self.on_apply)

        self.init_ui()

    def init_ui(self):
        self.SetTitle("Settings")

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Position Limits
        pos_lim_sizer = wx.BoxSizer(wx.VERTICAL)
        pos_lim_static_sizer = wx.StaticBoxSizer(wx.StaticBox(self.nb_settings_stage, wx.ID_ANY, "Position Limits"),
                                                 wx.HORIZONTAL)
        pos_lim_grid_sizer = wx.FlexGridSizer(4, 3, 5, 5)

        pos_lim_grid_sizer.Add((0, 0), 0, 0, 0)
        lbl_min = wx.StaticText(self.nb_settings_stage, wx.ID_ANY, "Minimum")
        pos_lim_grid_sizer.Add(lbl_min, 0, wx.ALIGN_CENTER, 0)
        lbl_max = wx.StaticText(self.nb_settings_stage, wx.ID_ANY, "Maximum")
        pos_lim_grid_sizer.Add(lbl_max, 0, wx.ALIGN_CENTER, 0)
        lbl_stage_x = wx.StaticText(self.nb_settings_stage, wx.ID_ANY, "X")
        pos_lim_grid_sizer.Add(lbl_stage_x, 0, wx.ALIGN_CENTER, 0)
        pos_lim_grid_sizer.Add(self.num_stage_x_min, 0, 0, 0)
        pos_lim_grid_sizer.Add(self.num_stage_x_max, 0, 0, 0)
        lbl_stage_y = wx.StaticText(self.nb_settings_stage, wx.ID_ANY, "Y")
        pos_lim_grid_sizer.Add(lbl_stage_y, 0, wx.ALIGN_CENTER, 0)
        pos_lim_grid_sizer.Add(self.num_stage_y_min, 0, 0, 0)
        pos_lim_grid_sizer.Add(self.num_stage_y_max, 0, 0, 0)
        lbl_stage_z = wx.StaticText(self.nb_settings_stage, wx.ID_ANY, "Z")
        pos_lim_grid_sizer.Add(lbl_stage_z, 0, wx.ALIGN_CENTER, 0)
        pos_lim_grid_sizer.Add(self.num_stage_z_min, 0, 0, 0)
        pos_lim_grid_sizer.Add(self.num_stage_z_max, 0, 0, 0)
        pos_lim_static_sizer.Add(pos_lim_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        pos_lim_sizer.Add(pos_lim_static_sizer, 1, wx.ALL | wx.EXPAND, 5)
        self.nb_settings_stage.SetSizer(pos_lim_sizer)
        self.nb_settings.AddPage(self.nb_settings_stage, "Stage")
        sizer.Add(self.nb_settings, 5, wx.ALL | wx.EXPAND, 5)

        # Buttons
        btn_sizer = wx.StdDialogButtonSizer()
        btn_sizer.AddButton(self.btn_cancel)
        btn_sizer.AddButton(self.btn_save)
        btn_sizer.AddButton(self.btn_apply)
        btn_sizer.Realize()

        sizer.Add(btn_sizer, 1, wx.ALIGN_RIGHT | wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_save(self, e):
        pass

    def on_apply(self, e):
        pass
