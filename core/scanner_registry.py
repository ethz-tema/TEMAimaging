import os
from importlib import import_module


class ScannerMeta(type):
    def __new__(mcs, name, bases, attrs):
        new_cls = super(ScannerMeta, mcs).__new__(mcs, name, bases, attrs)
        # noinspection PyTypeChecker
        register(new_cls)
        return new_cls


scanners_by_name = {}
scanners_by_display_name = {}
_param_map = {}


def _import_scanners():
    for m in os.listdir('scans'):
        import_module('scans.{}'.format(m.split('.')[0]))


def register(scanner):
    if hasattr(scanner, 'parameter_map'):
        _param_map.update(scanner.parameter_map)
    scanners_by_name[scanner.__name__] = scanner
    scanners_by_display_name[scanner.display_name] = scanner


def get_param_display_str(name):
    return _param_map.get(name)[0]


_import_scanners()
