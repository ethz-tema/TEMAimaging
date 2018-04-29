import wx
import wx.dataview


class Param:
    def __init__(self, step, key, key_name, value):
        self.step = step
        self.key = key
        self.key_name = key_name  # Displayed in param list
        self.value = value


class Step:
    def __init__(self, index, scan_type, scan_type_str, params):
        self.index = index
        self.scan_type = scan_type
        self.scan_type_str = scan_type_str
        self.params = params
        self.spot_size = 0
        self.frequency = 0
        self.shots_per_spot = 0
        self.cleaning_shot = False


class MeasurementViewModel(wx.dataview.PyDataViewModel):
    def __init__(self):
        super().__init__()

        # self.UseWeakRefs(False)

        self.steps = []

    def GetColumnCount(self):
        return 8

    def GetColumnType(self, col):
        mapper = {0: 'string', 1: 'PyObject', 2: 'PyObject', 3: 'PyObject', 4: 'PyObject', 5: 'PyObject', 6: 'PyObject',
                  7: 'PyObject'}
        return mapper[col]

    def HasContainerColumns(self, item):
        return True

    def GetChildren(self, item, children):
        if not item:  # root node
            for step in self.steps:
                children.append(self.ObjectToItem(step))
            return len(self.steps)

        node = self.ItemToObject(item)
        if isinstance(node, Step):
            for param in node.params.values():
                children.append(self.ObjectToItem(param))
            return len(node.params)
        return 0

    def IsContainer(self, item):
        if not item:  # root is container
            return True

        node = self.ItemToObject(item)
        if isinstance(node, Step):
            return True

        return False

    def GetParent(self, item):
        if not item:
            return wx.dataview.NullDataViewItem

        node = self.ItemToObject(item)
        if isinstance(node, Step):
            return wx.dataview.NullDataViewItem
        elif isinstance(node, Param):
            for s in self.steps:
                if s.index == node.step:
                    return self.ObjectToItem(s)

    def GetValue(self, item, col):
        node = self.ItemToObject(item)

        if isinstance(node, Step):
            mapper = {0: str(node.index), 1: (True, False, node.scan_type_str), 2: (False, False, ''),
                      3: (False, False, ''),
                      4: (True, True, str(node.spot_size)),
                      5: (True, True, str(node.frequency)), 6: (True, True, str(node.shots_per_spot)),
                      7: (True, node.cleaning_shot)}
            return mapper[col]

        elif isinstance(node, Param):
            mapper = {0: "", 1: (False, False, ''), 2: (True, False, str(node.key_name)),
                      3: (True, True, str(node.value)),
                      4: (False, False, ''),
                      5: (False, False, ''),
                      6: (False, False, ''), 7: (False, False)}
            return mapper[col]

    def SetValue(self, variant, item, col):
        node = self.ItemToObject(item)
        if isinstance(node, Step):
            if col == 4:
                node.spot_size = float(variant)
            if col == 5:
                node.frequency = float(variant)
            if col == 6:
                node.shots_per_spot = int(variant)
            if col == 7:
                node.cleaning_shot = variant
        elif isinstance(node, Param):
            if col == 3:
                node.value = float(variant)
        return True


measurement_model = MeasurementViewModel()
