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

from importlib import import_module

from tema_imaging.core.utils import get_project_root
from tema_imaging.scans import Scan

scanners_by_name = {}
scanners_by_display_name = {}
_param_map = {}


def _import_scanners() -> None:
    for m in (get_project_root() / "src/tema_imaging/scans").iterdir():
        import_module(f"tema_imaging.scans.{m.stem}")


def register(scanner) -> None:
    if hasattr(scanner, "disable") and scanner.disable:
        return

    if hasattr(scanner, "parameter_map"):
        _param_map.update(scanner.parameter_map)
    scanners_by_name[scanner.__name__] = scanner
    scanners_by_display_name[scanner.display_name] = scanner


def register_scan(scan_class: type[Scan]) -> type[Scan]:
    register(scan_class)

    return scan_class


def get_param_display_str(name):
    return _param_map.get(name)[0]


def get_param_scale_factor(name):
    return _param_map.get(name)[2]


_import_scanners()
