import copy
import logging
import threading

import wx
import wx.dataview

from core.conn_mgr import conn_mgr
from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import CompexLaserProtocol
from hardware.mcs_stage import MCSError, MCSStage


class MeasurementController:
    def __init__(self, laser, trigger, stage):
        self.laser = laser  # type: CompexLaserProtocol
        self.trigger = trigger  # type: ArduTrigger
        self.stage = stage  # type: MCSStage
        self.sequence = []

    def start_scan(self, scan):
        scan.set_instruments(self.laser, self.trigger, self.stage)
        stop_scan = threading.Event()

        class MeasureThread(threading.Thread):
            @classmethod
            def run(cls):
                try:
                    while scan.next_move() and not stop_scan.is_set():
                        scan.next_shot()
                except MCSError as e:
                    logging.exception(e)

        thread = MeasureThread()
        thread.start()

        return stop_scan

    def init_sequence(self, steps):
        self.sequence.clear()
        for step in steps:
            self.sequence.append(
                step.scan_type.from_params(step.spot_size, step.shots_per_spot, step.frequency, step.cleaning_shot,
                                           step.params))

    def start_sequence(self):
        stop_scan = threading.Event()

        class MeasureThread(threading.Thread):
            @classmethod
            def run(cls):
                try:
                    for scan in self.sequence:
                        scan.set_instruments(conn_mgr.laser, conn_mgr.trigger, conn_mgr.stage)
                        while scan.next_move() and not stop_scan.is_set():
                            scan.next_shot()
                except MCSError as e:
                    logging.exception(e)

        thread = MeasureThread()
        thread.start()

        return stop_scan


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

        self._steps = []

    @property
    def steps(self):
        return copy.deepcopy(self._steps)

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
            for step in self._steps:
                children.append(self.ObjectToItem(step))
            return len(self._steps)

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
            for s in self._steps:
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

    def _recalculate_ids(self):
        for i in range(len(self._steps)):
            step = self._steps[i]
            if step.index != i:
                step.index = i
                self.ItemChanged(self.ObjectToItem(step))

                for p in step.params.values():
                    p.step = i
                    self.ItemChanged(self.ObjectToItem(p))

    def delete_step(self, item):
        node = self.ItemToObject(item)
        if isinstance(node, Step):
            self._steps.remove(node)
            self.ItemDeleted(wx.dataview.NullDataViewItem, item)
            self._recalculate_ids()

    def append_step(self, typ, name):
        index = len(self._steps)
        params = {k: Param(index, k, v[0], v[1]) for k, v in typ.parameter_map.items()}
        step = Step(len(self._steps), typ, name, params)
        self._steps.append(step)
        step_item = self.ObjectToItem(step)
        self.ItemAdded(wx.dataview.NullDataViewItem, step_item)
        for param in step.params.values():
            self.ItemAdded(step_item, self.ObjectToItem(param))

    def insert_step(self, typ, name, position):
        index = len(self._steps)
        params = {k: Param(index, k, v[0], v[1]) for k, v in typ.parameter_map.items()}
        step = Step(len(self._steps), typ, name, params)
        self._steps.insert(position, step)
        step_item = self.ObjectToItem(step)
        self.ItemAdded(wx.dataview.NullDataViewItem, step_item)
        for param in step.params.values():
            self.ItemAdded(step_item, self.ObjectToItem(param))
        self._recalculate_ids()


measurement_model = MeasurementViewModel()
