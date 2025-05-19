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

from typing import Any

import wx
import wx.dataview


class SequenceEditorToggleRenderer(wx.dataview.DataViewCustomRenderer):
    def __init__(self) -> None:
        super().__init__('PyObject', wx.dataview.DATAVIEW_CELL_ACTIVATABLE)
        self.value = None

    def SetValue(self, value: Any) -> bool:
        self.value = value
        return True

    def GetValue(self) -> Any:
        return False

    def GetSize(self) -> wx.Size:
        return wx.RendererNative.Get().GetCheckBoxSize(self.GetView())

    def Render(self, cell: wx.Rect, dc: wx.DC, state: int) -> bool:
        if not self.value[0]:
            return True

        flags = 0
        if self.value[1]:
            flags |= wx.CONTROL_CHECKED

        wx.RendererNative.Get().DrawCheckBox(self.GetOwner().GetOwner(), dc, cell, flags)
        return True

    def ActivateCell(self, cell: wx.Rect, model: wx.dataview.DataViewModel, item: wx.dataview.DataViewItem, col: int,
                     mouseEvent: wx.MouseEvent) -> bool:
        if mouseEvent:
            if not wx.Rect(self.GetSize()).Contains(mouseEvent.GetPosition()):
                return False

            model.ChangeValue(not self.value[1], item, col)
            return True


class SequenceEditorTextRenderer(wx.dataview.DataViewCustomRenderer):
    def __init__(self) -> None:
        super().__init__('PyObject', wx.dataview.DATAVIEW_CELL_EDITABLE)
        self.value = ""

    def SetValue(self, value) -> bool:
        self.value = value
        return True

    def GetValue(self):
        return False

    def HasEditorCtrl(self) -> bool:
        return self.value[0] and self.value[1]

    def CreateEditorCtrl(self, parent: wx.Window, labelRect: wx.Rect, value) -> wx.Window:
        ctrl = wx.TextCtrl(parent,
                           value=value[2],
                           pos=labelRect.Position,
                           size=labelRect.Size)

        # select the text and put the caret at the end
        ctrl.SetInsertionPointEnd()
        ctrl.SelectAll()

        return ctrl

    def GetValueFromEditorCtrl(self, editor: wx.TextCtrl):
        return editor.GetValue()

    def Render(self, cell: wx.Rect, dc: wx.DC, state: int) -> bool:
        if not self.value[0]:
            return True

        self.RenderText(self.value[2], 0, cell, dc, state)
        return True

    def GetSize(self) -> wx.Size:
        if self.value[0] and self.value[2]:
            return self.GetTextExtent(self.value[2])

        return wx.Size(wx.dataview.DVC_DEFAULT_RENDERER_SIZE, wx.dataview.DVC_DEFAULT_RENDERER_SIZE)
