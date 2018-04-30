import wx

from scans import MeasurementController


class AddScanDialog(wx.Dialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.choice_scan_type = wx.Choice(self, wx.ID_ANY,
                                          choices=list(sorted(MeasurementController.scan_types.keys())))
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
