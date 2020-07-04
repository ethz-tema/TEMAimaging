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


class FloatValidator(wx.Validator):
    def __init__(self):
        super().__init__()
        self.Bind(wx.EVT_CHAR, self.on_char)

    def Clone(self):
        return FloatValidator()

    def Validate(self, parent):
        return True

    def on_char(self, event):
        key = event.GetKeyCode()
        ctrl = event.GetEventObject()

        if key in (wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_CONTROL_X, wx.WXK_CONTROL_A, wx.WXK_CONTROL_C):
            event.Skip()
            return
        elif key == wx.WXK_CONTROL_V:
            do = wx.TextDataObject()
            wx.TheClipboard.Open()
            success = wx.TheClipboard.GetData(do)
            wx.TheClipboard.Close()

            if not success:
                return None
            else:
                # Remove leading and trailing spaces before evaluating contents
                text = do.GetText().strip()

                try:
                    value = float(text)
                except ValueError:
                    return

                ctrl.SetValue(str(value))

        # Allow ASCII numerics
        if ord('0') <= key <= ord('9'):
            event.Skip()
            return

        # Allow decimal points and minus sign
        if key == ord('.') or key == ord('-'):
            event.Skip()
            return

        # Allow tabs, for tab navigation between TextCtrls
        if key == ord('\t'):
            event.Skip()
            return
