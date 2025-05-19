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

import collections
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Self, Type

from tema_imaging.core.settings import Settings
from tema_imaging.scans import Spot


class AxisType(Enum):
    X = 0
    Y = 1
    Z = 2


class AxisMovementMode(Enum):
    CL_RELATIVE = (0,)
    CL_ABSOLUTE = 1


class AxisStatus(Enum):
    STOPPED = (0,)
    MOVING = (1,)
    WAITING = 2


class StageError(Exception):
    pass


class EventHandler:
    # TODO: semantics for unregistering event handlers after scan is done
    def __init__(self) -> None:
        self._handlers: list[Callable[[Any | None], None]] = []

    def __iadd__(self, handler: Callable[[Any | None], None]) -> Self:
        if handler not in self._handlers:
            self._handlers.append(handler)
        return self

    def __isub__(self, handler: Callable[[Any | None], None]) -> Self:
        if handler in self._handlers:
            self._handlers.remove(handler)
        return self

    def __call__(self, *args, **kwargs) -> None:
        self._notify(*args, **kwargs)

    def _notify(self, *args, **kwargs) -> None:
        for handler in self._handlers:
            handler(*args, **kwargs)


class Axis(ABC):
    def __init__(self, name: str, channel: int) -> None:
        self._name = name
        self._channel = channel

    def __repr__(self) -> str:
        return "Name: {}, Channel: {}".format(self._name, self._channel)

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def move(self, value: int, auto_commit: bool = True) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def find_reference(self) -> None:
        pass

    @property
    @abstractmethod
    def is_referenced(self) -> bool:
        pass

    @property
    @abstractmethod
    def position(self) -> int:
        pass

    @property
    @abstractmethod
    def speed(self) -> int:
        pass

    @speed.setter
    @abstractmethod
    def speed(self, speed: int) -> None:
        pass

    @property
    @abstractmethod
    def position_limit(self) -> tuple[int, int]:
        pass

    @position_limit.setter
    @abstractmethod
    def position_limit(self, limit: tuple[int, int]) -> None:
        pass

    @property
    @abstractmethod
    def movement_mode(self) -> AxisMovementMode:
        pass

    @movement_mode.setter
    @abstractmethod
    def movement_mode(self, value: AxisMovementMode) -> None:
        pass

    @property
    @abstractmethod
    def status(self) -> AxisStatus:
        pass


class MovementQueue(collections.deque[dict[AxisType, float]]):
    def __init__(self) -> None:
        super().__init__()
        self.on_queue_finished = EventHandler()

    def put(self, item: Spot | dict[AxisType, float]) -> None:
        if isinstance(item, Spot):
            item = {AxisType.X: item.X, AxisType.Y: item.Y, AxisType.Z: item.Z}
            super().appendleft(item)
        elif isinstance(item, dict):
            super().appendleft(item)
        else:
            raise ValueError("Invalid frame passed to movement queue.")


class Stage(ABC):
    def __init__(self) -> None:
        self.movement_queue = MovementQueue()
        self.on_movement_completed = EventHandler()
        self.on_frame_completed = EventHandler()
        self._axes = {}
        self._connected = False

    @abstractmethod
    def connect(self) -> None:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def axes(self) -> dict[AxisType, Axis]:
        return self._axes

    @abstractmethod
    def stop_all(self) -> None:
        for ax in self.axes:
            ax.stop()

    def find_references(self) -> None:
        if Settings.get("stage.ref_x"):
            self.axes[AxisType.X].find_reference()
        if Settings.get("stage.ref_y"):
            self.axes[AxisType.Y].find_reference()
        if Settings.get("stage.ref_z"):
            self.axes[AxisType.Z].find_reference()

    @property
    def axes_type(self) -> Type[AxisType]:
        if self._num_channels == 3:
            return AxisType
        else:
            raise ValueError("Not supported channel count.")

    @property
    @abstractmethod
    def _num_channels(self) -> int:
        pass

    @abstractmethod
    def trigger_frame(self) -> None:
        pass

    @abstractmethod
    def commit_move(self) -> None:
        pass
