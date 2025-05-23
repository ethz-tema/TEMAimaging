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

from tema_imaging.core.conn_mgr import conn_mgr
from tema_imaging.core.settings import Settings
from tema_imaging.hardware.camera import Camera, camera_resolutions


class ConnectionManagerDialog(wx.Dialog):
    def __init__(self, parent: wx.Window) -> None:
        super().__init__(parent)

        rate_choices = ["9600", "19200"]

        # Laser
        self.stxt_laser_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_laser_port = wx.ComboBox(
            self, wx.ID_ANY, choices=["/dev/ttyUSB0", "/dev/ttyUSB1"]
        )
        self.choice_laser_rate = wx.Choice(self, wx.ID_ANY, choices=rate_choices)
        self.btn_laser_connect = wx.Button(self, wx.ID_ANY)

        # Trigger
        self.stxt_trigger_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_trigger_port = wx.ComboBox(
            self, wx.ID_ANY, choices=["/dev/ttyACM0", "/dev/ttyACM1"]
        )
        self.choice_trigger_rate = wx.Choice(self, wx.ID_ANY, choices=rate_choices)
        self.btn_trigger_connect = wx.Button(self, wx.ID_ANY)

        # Shutter
        self.stxt_shutter_status = wx.StaticText(self, wx.ID_ANY)
        self.num_shutter_output = wx.SpinCtrl(self, wx.ID_ANY, min=1, max=32)
        self.btn_shutter_connect = wx.Button(self, wx.ID_ANY)

        # Stage
        self.stxt_stage_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_stage_port = wx.ComboBox(self, wx.ID_ANY, choices=["usb:ix:0"])
        self.btn_stage_connect = wx.Button(self, wx.ID_ANY)

        # Camera
        self.stxt_camera_status = wx.StaticText(self, wx.ID_ANY)
        self.choice_camera_driver = wx.Choice(self, wx.ID_ANY, choices=["uEye", "v4l2"])
        self.choice_camera_port = wx.Choice(self, wx.ID_ANY, choices=[])
        self.choice_camera_port.SetMinSize((120, -1))
        self.choice_camera_resolution = wx.Choice(
            self, wx.ID_ANY, choices=list(camera_resolutions.keys())
        )
        self.btn_camera_connect = wx.Button(self, wx.ID_ANY)

        self.chk_auto_connect = wx.CheckBox(
            self, wx.ID_ANY, "Connect devices on startup"
        )

        self.btn_save = wx.Button(self, wx.ID_SAVE)
        self.btn_save.SetDefault()
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL)

        self.init_ui()
        self.Layout()

    def init_ui(self) -> None:
        self.SetTitle("Connection Manager")

        sizer = wx.BoxSizer(wx.VERTICAL)

        lbl_status_laser = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_trigger = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_shutter = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_stage = wx.StaticText(self, wx.ID_ANY, "Status:")
        lbl_status_camera = wx.StaticText(self, wx.ID_ANY, "Status:")

        lbl_port_laser = wx.StaticText(self, wx.ID_ANY, "Port:")
        lbl_port_trigger = wx.StaticText(self, wx.ID_ANY, "Port:")
        lbl_port_stage = wx.StaticText(self, wx.ID_ANY, "Port:")
        lbl_port_camera = wx.StaticText(self, wx.ID_ANY, "Port:")

        lbl_camera_resolution = wx.StaticText(self, wx.ID_ANY, "Resolution:")
        lbl_camera_driver = wx.StaticText(self, wx.ID_ANY, "Driver:")

        lbl_rate_laser = wx.StaticText(self, wx.ID_ANY, "Baud Rate:")
        lbl_rate_trigger = wx.StaticText(self, wx.ID_ANY, "Baud Rate:")

        def fill_sizer(s: wx.Sizer, count: int) -> None:
            for c in range(count):
                s.Add((0, 0), 0, 0, 0)

        # Laser
        laser_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Laser"), wx.VERTICAL
        )
        laser_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        laser_grid_sizer.Add(lbl_status_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.stxt_laser_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(laser_grid_sizer, 2)
        laser_grid_sizer.Add(lbl_port_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.choice_laser_port, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(lbl_rate_laser, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        laser_grid_sizer.Add(self.choice_laser_rate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(laser_grid_sizer, 3)
        laser_grid_sizer.Add(self.btn_laser_connect, 0, 0, 0)

        laser_sizer.Add(laser_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(laser_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Trigger
        trigger_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Trigger"), wx.VERTICAL
        )
        trigger_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        trigger_grid_sizer.Add(lbl_status_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.stxt_trigger_status, 0, 0, 0)
        fill_sizer(trigger_grid_sizer, 2)
        trigger_grid_sizer.Add(lbl_port_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.choice_trigger_port, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(lbl_rate_trigger, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        trigger_grid_sizer.Add(self.choice_trigger_rate, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(trigger_grid_sizer, 3)
        trigger_grid_sizer.Add(self.btn_trigger_connect, 0, 0, 0)

        trigger_sizer.Add(trigger_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(trigger_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Shutter
        shutter_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Shutter"), wx.VERTICAL
        )
        shutter_grid_sizer = wx.FlexGridSizer(3, 4, 5, 5)

        shutter_grid_sizer.Add(lbl_status_shutter, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add(self.stxt_shutter_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(shutter_grid_sizer, 2)
        lbl_output = wx.StaticText(self, wx.ID_ANY, "Output:")
        shutter_grid_sizer.Add(lbl_output, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        shutter_grid_sizer.Add(self.num_shutter_output, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(shutter_grid_sizer, 5)
        shutter_grid_sizer.Add(self.btn_shutter_connect, 0, 0, 0)
        shutter_grid_sizer.AddGrowableCol(2)

        shutter_sizer.Add(shutter_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(shutter_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Stage
        stage_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Stage"), wx.VERTICAL
        )
        stage_grid_sizer = wx.FlexGridSizer(0, 4, 5, 5)

        stage_grid_sizer.Add(lbl_status_stage, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        stage_grid_sizer.Add(self.stxt_stage_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(stage_grid_sizer, 2)
        stage_grid_sizer.Add(lbl_port_stage, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        stage_grid_sizer.Add(self.choice_stage_port, 0, 0, 0)
        fill_sizer(stage_grid_sizer, 5)
        stage_grid_sizer.Add(self.btn_stage_connect, 0, 0, 0)
        stage_grid_sizer.AddGrowableCol(2)

        stage_sizer.Add(stage_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(stage_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Camera
        camera_sizer = wx.StaticBoxSizer(
            wx.StaticBox(self, wx.ID_ANY, "Camera"), wx.VERTICAL
        )
        camera_grid_sizer = wx.FlexGridSizer(0, 4, 5, 5)

        camera_grid_sizer.Add(lbl_status_camera, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        camera_grid_sizer.Add(self.stxt_camera_status, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        fill_sizer(camera_grid_sizer, 2)
        camera_grid_sizer.Add(lbl_camera_driver, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        camera_grid_sizer.Add(self.choice_camera_driver, 0, 0, 0)
        camera_grid_sizer.Add(lbl_port_camera, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        camera_grid_sizer.Add(self.choice_camera_port, 0, 0, 0)
        camera_grid_sizer.Add(lbl_camera_resolution, 0, wx.ALIGN_CENTER_VERTICAL, 0)
        camera_grid_sizer.Add(self.choice_camera_resolution, 0, 0, 0)

        fill_sizer(camera_grid_sizer, 5)
        camera_grid_sizer.Add(self.btn_camera_connect, 0, 0, 0)
        camera_grid_sizer.AddGrowableCol(2)

        camera_sizer.Add(camera_grid_sizer, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(camera_sizer, 0, wx.ALL | wx.EXPAND, 5)

        # Auto-connect
        sizer.Add(self.chk_auto_connect, 0, wx.LEFT | wx.BOTTOM, 5)
        self.chk_auto_connect.SetValue(Settings.get("general.connect_on_startup"))

        # Buttons
        sizer_buttons = wx.StdDialogButtonSizer()
        sizer_buttons.AddButton(self.btn_save)
        sizer_buttons.AddButton(self.btn_cancel)
        sizer_buttons.Realize()
        sizer.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.BOTTOM, 12)

        self.Bind(
            wx.EVT_CHOICE,
            self.on_choice_camera_driver_choice,
            self.choice_camera_driver,
        )

        self.choice_laser_port.SetValue(Settings.get("laser.conn.port"))
        self.choice_laser_rate.SetSelection(
            self.choice_laser_rate.FindString(str(Settings.get("laser.conn.rate")))
        )
        self.choice_trigger_port.SetValue(Settings.get("trigger.conn.port"))
        self.choice_trigger_rate.SetSelection(
            self.choice_trigger_rate.FindString(str(Settings.get("trigger.conn.rate")))
        )
        self.num_shutter_output.SetValue(Settings.get("shutter.output"))
        self.choice_stage_port.SetValue(Settings.get("stage.conn.port"))

        self.choice_camera_driver.SetSelection(
            self.choice_camera_driver.FindString(str(Settings.get("camera.driver")))
        )
        self.choice_camera_port.Set(
            Camera.get_driver_from_name(
                str(Settings.get("camera.driver"))
            ).get_device_ids()
        )
        self.choice_camera_port.SetSelection(
            self.choice_camera_port.FindString(str(Settings.get("camera.conn.port")))
        )
        self.choice_camera_resolution.SetSelection(
            self.choice_camera_resolution.FindString(
                str(Settings.get("camera.resolution"))
            )
        )

        self.on_connection_changed_laser(conn_mgr.laser_connected)
        self.on_connection_changed_trigger(conn_mgr.trigger_connected)
        self.on_connection_changed_shutter(conn_mgr.shutter_connected)
        self.on_connection_changed_stage(conn_mgr.stage_connected)
        self.on_connection_changed_camera(conn_mgr.camera_connected)

        self.Bind(wx.EVT_BUTTON, self.on_click_laser, self.btn_laser_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_trigger, self.btn_trigger_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_shutter, self.btn_shutter_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_stage, self.btn_stage_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_camera, self.btn_camera_connect)
        self.Bind(wx.EVT_BUTTON, self.on_click_save, self.btn_save)
        self.Bind(wx.EVT_BUTTON, self.on_click_cancel, self.btn_cancel)

        pub.subscribe(self.on_connection_changed_laser, "laser.connection_changed")
        pub.subscribe(self.on_connection_changed_trigger, "trigger.connection_changed")
        pub.subscribe(self.on_connection_changed_shutter, "shutter.connection_changed")
        pub.subscribe(self.on_connection_changed_stage, "stage.connection_changed")
        pub.subscribe(self.on_connection_changed_camera, "camera.connection_changed")

        self.SetSizer(sizer)
        sizer.Fit(self)

    def on_click_cancel(self, e: wx.CommandEvent) -> None:
        self.EndModal(wx.ID_CANCEL)

    def on_click_save(self, e: wx.CommandEvent):
        Settings.set("laser.conn.port", self.choice_laser_port.GetValue())
        Settings.set(
            "laser.conn.rate", int(self.choice_laser_rate.GetStringSelection())
        )

        Settings.set("trigger.conn.port", self.choice_trigger_port.GetValue())
        Settings.set(
            "trigger.conn.rate", int(self.choice_trigger_rate.GetStringSelection())
        )

        Settings.set("shutter.output", self.num_shutter_output.GetValue())

        Settings.set("stage.conn.port", self.choice_stage_port.GetValue())

        Settings.set("camera.driver", self.choice_camera_driver.GetStringSelection())
        Settings.set("camera.conn.port", self.choice_camera_port.GetStringSelection())
        Settings.set(
            "camera.resolution", self.choice_camera_resolution.GetStringSelection()
        )

        Settings.set("general.connect_on_startup", self.chk_auto_connect.GetValue())
        Settings.save()

        self.EndModal(wx.ID_SAVE)

    def on_click_laser(self, _: wx.CommandEvent) -> None:
        if conn_mgr.laser_connected:
            conn_mgr.laser_disconnect()
        else:
            conn_mgr.laser_connect(
                self.choice_laser_port.GetValue(),
                self.choice_laser_rate.GetStringSelection(),
            )

    def on_click_trigger(self, _: wx.CommandEvent):
        if conn_mgr.trigger_connected:
            conn_mgr.trigger_disconnect()
        else:
            conn_mgr.trigger_connect(
                self.choice_trigger_port.GetValue(),
                self.choice_trigger_rate.GetStringSelection(),
            )

    def on_click_shutter(self, _: wx.CommandEvent):
        if conn_mgr.shutter_connected:
            conn_mgr.shutter_disconnect()
        else:
            conn_mgr.shutter_connect(self.num_shutter_output.GetValue())

    def on_click_stage(self, _: wx.CommandEvent):
        if conn_mgr.stage_connected:
            conn_mgr.stage_disconnect()
        else:
            conn_mgr.stage_connect(self.choice_stage_port.GetValue())

    def on_click_camera(self, _: wx.CommandEvent):
        if conn_mgr.camera_connected:
            conn_mgr.camera_disconnect()
        else:
            conn_mgr.camera_connect(
                self.choice_camera_driver.GetStringSelection(),
                self.choice_camera_port.GetStringSelection(),
                camera_resolutions[self.choice_camera_resolution.GetStringSelection()],
            )

    def on_choice_camera_driver_choice(self, e: wx.CommandEvent) -> None:
        self.choice_camera_port.Set(
            Camera.get_driver_from_name(e.GetString()).get_device_ids()
        )
        self.choice_camera_port.SetSelection(0)
        self.choice_camera_port.Fit()

    def on_connection_changed_laser(self, connected: bool) -> None:
        if connected:
            self.stxt_laser_status.SetLabel("Connected")
            self.stxt_laser_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_laser_connect.SetLabel("Disconnect")
        else:
            self.stxt_laser_status.SetLabel("Disconnected")
            self.stxt_laser_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_laser_connect.SetLabel("Connect")

    def on_connection_changed_trigger(self, connected: bool) -> None:
        if connected:
            self.stxt_trigger_status.SetLabel("Connected")
            self.stxt_trigger_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_trigger_connect.SetLabel("Disconnect")
        else:
            self.stxt_trigger_status.SetLabel("Disconnected")
            self.stxt_trigger_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_trigger_connect.SetLabel("Connect")

    def on_connection_changed_shutter(self, connected: bool) -> None:
        if connected:
            self.stxt_shutter_status.SetLabel("Connected")
            self.stxt_shutter_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_shutter_connect.SetLabel("Disconnect")
        else:
            self.stxt_shutter_status.SetLabel("Disconnected")
            self.stxt_shutter_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_shutter_connect.SetLabel("Connect")

    def on_connection_changed_stage(self, connected: bool) -> None:
        if connected:
            self.stxt_stage_status.SetLabel("Connected")
            self.stxt_stage_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_stage_connect.SetLabel("Disconnect")
        else:
            self.stxt_stage_status.SetLabel("Disconnected")
            self.stxt_stage_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_stage_connect.SetLabel("Connect")

    def on_connection_changed_camera(self, connected: bool) -> None:
        if connected:
            self.stxt_camera_status.SetLabel("Connected")
            self.stxt_camera_status.SetForegroundColour(wx.Colour((0, 150, 0)))
            self.btn_camera_connect.SetLabel("Disconnect")
        else:
            self.stxt_camera_status.SetLabel("Disconnected")
            self.stxt_camera_status.SetForegroundColour(wx.Colour((255, 0, 0)))
            self.btn_camera_connect.SetLabel("Connect")
