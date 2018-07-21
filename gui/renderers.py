import wx
import wx.dataview


class SequenceEditorToggleRenderer(wx.dataview.DataViewCustomRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__('PyObject', wx.dataview.DATAVIEW_CELL_ACTIVATABLE, *args, **kwargs)
        self.value = None

    def SetValue(self, value):
        self.value = value
        return True

    def GetValue(self):
        return False

    def GetSize(self):
        return wx.RendererNative.Get().GetCheckBoxSize(self.GetView())

    def Render(self, cell, dc, state):
        if not self.value[0]:
            return True

        flags = 0
        if self.value[1]:
            flags |= wx.CONTROL_CHECKED

        wx.RendererNative.Get().DrawCheckBox(self.GetOwner().GetOwner(), dc, cell, flags)
        return True

    def ActivateCell(self, cell, model, item, col, mouseEvent):
        if mouseEvent:
            if not wx.Rect(self.GetSize()).Contains(mouseEvent.GetPosition()):
                return False

            model.ChangeValue(not self.value[1], item, col)
            return True


class SequenceEditorTextRenderer(wx.dataview.DataViewCustomRenderer):
    def __init__(self, *args, **kwargs):
        super().__init__('PyObject', wx.dataview.DATAVIEW_CELL_EDITABLE, *args, **kwargs)
        self.value = ""

    def SetValue(self, value):
        self.value = value
        return True

    def GetValue(self):
        return False

    def HasEditorCtrl(self):
        return self.value[0] and self.value[1]

    def CreateEditorCtrl(self, parent, labelRect, value):
        ctrl = wx.TextCtrl(parent,
                           value=value[2],
                           pos=labelRect.Position,
                           size=labelRect.Size)

        # select the text and put the caret at the end
        ctrl.SetInsertionPointEnd()
        ctrl.SelectAll()

        return ctrl

    def GetValueFromEditorCtrl(self, editor):
        return editor.GetValue()

    def Render(self, cell, dc, state):
        if not self.value[0]:
            return True

        self.RenderText(self.value[2], 0, cell, dc, state)
        return True

    def GetSize(self):
        if self.value[0] and self.value[2]:
            return self.GetTextExtent(self.value[2])

        return wx.Size(wx.dataview.DVC_DEFAULT_RENDERER_SIZE, wx.dataview.DVC_DEFAULT_RENDERER_SIZE)
