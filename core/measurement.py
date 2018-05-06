import copy
import logging
import threading

import wx
import wx.dataview
from ruamel.yaml import YAML

import core.scanner_registry
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
                        while scan.next_move() and not stop_scan.is_set():
                            scan.next_shot()
                except MCSError as e:
                    logging.exception(e)

        thread = MeasureThread()
        thread.start()

        return stop_scan


class Param:
    def __init__(self, step_index, key, value):
        self.step_index = step_index
        self.key = key
        self.value = value

    def __getstate__(self):
        return {'value': self.value}

    def __setstate__(self, state):
        self.value = state['value']


class Step:
    def __init__(self, index, scan_type, params):
        self.index = index
        self.scan_type = scan_type
        self.params = params
        self.spot_size = 0
        self.frequency = 0
        self.shots_per_spot = 0
        self.cleaning_shot = False

    def __getstate__(self):
        return {
            'scan_type': self.scan_type.__name__,
            'params': self.params,
            'spot_size': self.spot_size,
            'frequency': self.frequency,
            'shots_per_spot': self.shots_per_spot,
            'cleaning_shot': self.cleaning_shot}

    def __setstate__(self, state):
        self.index = None
        for k, v in state.items():
            if k == 'params':
                self.params = {}
                for param_k, param_v in v.items():
                    param_v.step_index = None
                    param_v.key = param_k
                    self.params[param_k] = param_v
            elif k == 'scan_type':
                self.scan_type = core.scanner_registry.scanners_by_name.get(v)
            else:
                setattr(self, k, v)


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
            for param in sorted(node.params.values(), key=lambda k: k.key):
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
                if s.index == node.step_index:
                    return self.ObjectToItem(s)

    def GetValue(self, item, col):
        node = self.ItemToObject(item)

        if isinstance(node, Step):
            mapper = {0: str(node.index), 1: (True, False, node.scan_type.display_name), 2: (False, False, ''),
                      3: (False, False, ''),
                      4: (True, True, str(node.spot_size)),
                      5: (True, True, str(node.frequency)), 6: (True, True, str(node.shots_per_spot)),
                      7: (True, node.cleaning_shot)}
            return mapper[col]

        elif isinstance(node, Param):
            mapper = {0: "", 1: (False, False, ''),
                      2: (True, False, str(core.scanner_registry.get_param_display_str(node.key))),
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

    def _recalculate_ids(self, notify=True):
        for i in range(len(self._steps)):
            step = self._steps[i]
            if step.index != i:
                step.index = i
                if notify:
                    self.ItemChanged(self.ObjectToItem(step))

                for p in step.params.values():
                    p.step_index = i
                    if notify:
                        self.ItemChanged(self.ObjectToItem(p))

    def dump_model(self, stream):
        yaml = YAML()
        yaml.register_class(Step)
        yaml.register_class(Param)

        yaml.dump(self._steps, stream)

    def load_model(self, stream):
        yaml = YAML()
        yaml.register_class(Step)
        yaml.register_class(Param)

        self._steps = []
        self.Cleared()
        self._steps = yaml.load(stream)

        self._recalculate_ids(False)
        for step in self._steps:
            step_item = self.ObjectToItem(step)
            self.ItemAdded(wx.dataview.NullDataViewItem, step_item)
            for param in step.params.values():
                self.ItemAdded(step_item, self.ObjectToItem(param))

    def delete_step(self, item):
        node = self.ItemToObject(item)
        if isinstance(node, Step):
            self._steps.remove(node)
            self.ItemDeleted(wx.dataview.NullDataViewItem, item)
            self._recalculate_ids()

    def append_step(self, typ):
        index = len(self._steps)
        params = {k: Param(index, k, v[1]) for k, v in typ.parameter_map.items()}
        step = Step(len(self._steps), typ, params)
        self._steps.append(step)
        step_item = self.ObjectToItem(step)
        self.ItemAdded(wx.dataview.NullDataViewItem, step_item)
        for param in step.params.values():
            self.ItemAdded(step_item, self.ObjectToItem(param))

    def insert_step(self, typ, position):
        index = len(self._steps)
        params = {k: Param(index, k, v[1]) for k, v in typ.parameter_map.items()}
        step = Step(len(self._steps), typ, params)
        self._steps.insert(position, step)
        step_item = self.ObjectToItem(step)
        self.ItemAdded(wx.dataview.NullDataViewItem, step_item)
        for param in step.params.values():
            self.ItemAdded(step_item, self.ObjectToItem(param))
        self._recalculate_ids()


measurement_model = MeasurementViewModel()
