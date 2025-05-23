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
from PIL import Image
from pubsub import pub

import tema_imaging.hardware.laser_compex
from tema_imaging.core.conn_mgr import conn_mgr
from tema_imaging.core.settings import Settings
from tema_imaging.gui.camera_frame import CameraFrame
from tema_imaging.gui.conn_mgr import ConnectionManagerDialog
from tema_imaging.gui.dialogs import AboutDialog, LaserStatusDialog
from tema_imaging.gui.panels import (
    CameraPanel,
    LaserManualShootPanel,
    LaserPanel,
    MeasurementPanel,
    ScanCtrlPanel,
    StagePanel,
)
from tema_imaging.gui.preferences import PreferencesDialog
from tema_imaging.hardware.camera import Camera
from tema_imaging.hardware.stage import AxisType


class MainFrame(wx.Frame):
    def __init__(self, title: str) -> None:
        super().__init__(None, title=title)

        icon = wx.Icon("logo.png")
        self.SetIcon(icon)

        self.status_bar = self.CreateStatusBar(2)

        self.laser_menu_status = wx.MenuItem(
            id=wx.ID_ANY, text="Status", helpString="Laser status"
        )

        self.stage_menu_reference = wx.MenuItem(
            id=wx.ID_ANY, text="Reference axes", helpString="Reference stage axes"
        )
        self.stage_menu_reset_speed = wx.MenuItem(
            id=wx.ID_ANY, text="Reset speed", helpString="Reset axis speeds"
        )

        self.help_menu_about = wx.MenuItem(
            id=wx.ID_ANY, text="About", helpString="Show information about the software"
        )

        self.main_panel = wx.Panel(self)
        self.laser_panel = LaserPanel(self.main_panel)
        self.stage_panel = StagePanel(self.main_panel)
        self.laser_manual_shoot_panel = LaserManualShootPanel(self.main_panel)
        self.scan_ctrl_panel = ScanCtrlPanel(self.main_panel)
        self.measurement_panel = MeasurementPanel(self.main_panel)
        self.camera_panel = CameraPanel(self.main_panel)

        self.init_ui()

    def init_ui(self) -> None:
        file_menu = wx.Menu()
        file_menu_conn_mgr = file_menu.Append(
            wx.ID_ANY, "Connection Manager", "Open connection manager"
        )
        file_menu_settings = file_menu.Append(wx.ID_PREFERENCES)
        file_menu.Append(wx.ID_SEPARATOR)
        file_menu_close = file_menu.Append(wx.ID_EXIT)

        laser_menu = wx.Menu()
        laser_menu.Append(self.laser_menu_status)

        stage_menu = wx.Menu()
        stage_menu.Append(self.stage_menu_reference)
        stage_menu.Append(self.stage_menu_reset_speed)

        help_menu = wx.Menu()
        help_menu.Append(self.help_menu_about)

        if not conn_mgr.laser_connected:
            self.laser_menu_status.Enable(False)

        if not conn_mgr.stage_connected:
            self.stage_menu_reference.Enable(False)
            self.stage_menu_reset_speed.Enable(False)

        menubar = wx.MenuBar()
        menubar.Append(file_menu, "&File")
        menubar.Append(laser_menu, "&Laser")
        menubar.Append(stage_menu, "&Stage")
        menubar.Append(help_menu, "Help")
        self.SetMenuBar(menubar)

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        vert_sizer = wx.BoxSizer(wx.VERTICAL)
        vert_sizer.Add(self.camera_panel, 0, wx.BOTTOM, border=5)
        self.camera_panel.Show(
            not Settings.get("camera.separate_window") and conn_mgr.camera_connected
        )
        vert_sizer.Add(self.laser_panel, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(self.stage_panel, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(self.laser_manual_shoot_panel, 0, wx.BOTTOM, border=5)
        vert_sizer.Add(self.scan_ctrl_panel, 0, wx.ALL, border=0)

        sizer.Add(self.measurement_panel, 1, wx.ALL | wx.EXPAND, border=10)
        sizer.Add(vert_sizer, 0, wx.TOP | wx.RIGHT | wx.BOTTOM, border=10)

        self.Bind(wx.EVT_MENU, self.on_connection_manager, file_menu_conn_mgr)
        self.Bind(wx.EVT_MENU, self.on_settings, file_menu_settings)
        self.Bind(wx.EVT_MENU, self.on_quit, file_menu_close)
        self.Bind(wx.EVT_MENU, self.on_click_laser_menu_status, self.laser_menu_status)
        self.Bind(
            wx.EVT_MENU, self.on_click_stage_menu_reference, self.stage_menu_reference
        )
        self.Bind(
            wx.EVT_MENU,
            self.on_click_stage_menu_reset_speed,
            self.stage_menu_reset_speed,
        )
        self.Bind(wx.EVT_MENU, self.on_click_help_menu_about, self.help_menu_about)

        self.Bind(wx.EVT_CLOSE, self.on_quit)

        pub.subscribe(self.on_laser_status_changed, "laser.status_changed")
        pub.subscribe(self.on_laser_connection_changed, "laser.connection_changed")
        pub.subscribe(self.on_stage_connection_changed, "stage.connection_changed")
        pub.subscribe(self.on_camera_connection_changed, "camera.connection_changed")
        pub.subscribe(self.on_measurement_step_changed, "measurement.step_changed")
        pub.subscribe(self.on_measurement_done, "measurement.done")
        pub.subscribe(self.on_image_acquired, "camera.image_acquired")

        self.main_panel.SetSizerAndFit(sizer)
        sizer.SetSizeHints(self)

        pub.sendMessage("gui.startup_finished")

    def on_stage_connection_changed(self, connected: bool) -> None:
        if connected:
            self.stage_menu_reference.Enable(True)
            self.stage_menu_reset_speed.Enable(True)
        else:
            self.stage_menu_reference.Enable(False)
            self.stage_menu_reset_speed.Enable(False)

    def on_camera_connection_changed(self, connected: bool) -> None:
        if Settings.get("camera.separate_window"):
            if connected:
                frame = CameraFrame(self)
                frame.Show()

        self.camera_panel.Show(not Settings.get("camera.separate_window") and connected)
        self.main_panel.Fit()
        self.main_panel.GetParent().Fit()

    def on_connection_manager(self, _: wx.CommandEvent) -> None:
        with ConnectionManagerDialog(self) as dlg:
            dlg.ShowModal()

    def on_settings(self, _: wx.CommandEvent) -> None:
        with PreferencesDialog(self) as dlg:
            dlg.ShowModal()

    def on_laser_status_changed(
        self, status: tema_imaging.hardware.laser_compex.OpMode
    ) -> None:
        self.status_bar.SetStatusText("Laser status: " + str(status), 0)

    def on_measurement_step_changed(self, current_step: int) -> None:
        self.status_bar.SetStatusText("Current step: {}".format(current_step), 1)

    def on_measurement_done(self, duration: float) -> None:
        self.status_bar.SetStatusText("", 1)

    def on_laser_connection_changed(self, connected: bool) -> None:
        if connected:
            self.laser_menu_status.Enable(True)
        else:
            self.laser_menu_status.Enable(False)

    def on_quit(self, _: wx.CloseEvent | wx.CommandEvent) -> None:
        conn_mgr.laser_disconnect()
        conn_mgr.trigger_disconnect()
        conn_mgr.shutter_disconnect()
        conn_mgr.stage_disconnect()
        conn_mgr.camera_disconnect()
        self.Destroy()

    def on_click_laser_menu_status(self, _: wx.CommandEvent) -> None:
        with LaserStatusDialog(self) as dlg:
            dlg.ShowModal()

    @staticmethod
    def on_click_stage_menu_reference(_: wx.CommandEvent) -> None:
        conn_mgr.stage.find_references()

    @staticmethod
    def on_click_stage_menu_reset_speed(_: wx.CommandEvent) -> None:
        conn_mgr.stage.axes[AxisType.X].speed = 0
        conn_mgr.stage.axes[AxisType.Y].speed = 0
        conn_mgr.stage.axes[AxisType.Z].speed = 0

    def on_image_acquired(self, _: Camera, image: Image.Image) -> None:
        wx.CallAfter(self.camera_panel.update_image, image)

    @staticmethod
    def on_click_help_menu_about(_: wx.CommandEvent) -> None:
        AboutDialog()
