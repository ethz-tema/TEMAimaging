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

import abc
import datetime
import time
from pathlib import Path
from typing import TYPE_CHECKING, final

from tema_imaging.core.utils import get_project_root

if TYPE_CHECKING:
    from tema_imaging.core.measurement import Measurement


class Spot:
    def __init__(self, x: float, y: float, z: float | None = None):
        self.X = x
        self.Y = y
        self.Z = z


class Scan(abc.ABC):
    _meas_log_dir = Path(get_project_root() / "logs")

    def __init__(self):
        self._meas_log_path: Path | None = None
        self._start_timestamp = 0.0

    @final
    def init_scan(self, measurement: "Measurement") -> None:
        self._meas_log_dir.mkdir(parents=True, exist_ok=True)

        self._init_scan(measurement)
        self._start_timestamp = time.time()

        self._meas_log_path = (
            self._meas_log_dir
            / f"measurement_{datetime.datetime.now().isoformat()}.txt"
        )
        self._meas_log_path.touch()

    @abc.abstractmethod
    def _init_scan(self, measurement: "Measurement") -> None:
        pass

    def log_spot(self, spot: Spot) -> None:
        if self._meas_log_path is None:
            return

        if spot.Z is None:
            spot_str = f"{spot.X},{spot.Y}"
        else:
            spot_str = f"{spot.X},{spot.Y},{spot.Z}"

        with self._meas_log_path.open("a") as f:
            f.write(f"{time.time() - self._start_timestamp},{spot_str}\n")
