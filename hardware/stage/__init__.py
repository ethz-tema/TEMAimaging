import collections
from abc import abstractmethod, ABC
from enum import Enum
from typing import Tuple, Dict, Type, Callable

from core.settings import Settings
from scans import Spot


class AxisType(Enum):
    X = 0
    Y = 1
    Z = 2


class AxisMovementMode(Enum):
    CL_RELATIVE = 0,
    CL_ABSOLUTE = 1


class AxisStatus(Enum):
    STOPPED = 0,
    MOVING = 1,
    WAITING = 2


class EventHandler:
    # TODO: semantics for unregistering event handlers after scan is done
    def __init__(self):
        self._handlers = []

    def __iadd__(self, handler: Callable):
        if handler not in self._handlers:
            self._handlers.append(handler)
        return self

    def __isub__(self, handler: Callable):
        if handler in self._handlers:
            self._handlers.remove(handler)
        return self

    def __call__(self, *args, **kwargs):
        self._notify(*args, **kwargs)

    def _notify(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)


class Axis(ABC):
    def __init__(self, channel: int, stage: 'Stage'):
        self._channel = channel
        self._stage = stage

    @abstractmethod
    def move(self, value: int):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def find_reference(self):
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
    def speed(self, speed: int):
        pass

    @property
    @abstractmethod
    def position_limit(self) -> Tuple[int, int]:
        pass

    @position_limit.setter
    @abstractmethod
    def position_limit(self, limit: Tuple[int, int]):
        pass

    @property
    @abstractmethod
    def movement_mode(self) -> AxisMovementMode:
        pass

    @movement_mode.setter
    @abstractmethod
    def movement_mode(self, value: AxisMovementMode):
        pass

    @property
    @abstractmethod
    def status(self) -> AxisStatus:
        pass


class MovementQueue(collections.deque):
    def __init__(self):
        super().__init__()
        self.on_queue_finished = EventHandler()

    def put(self, item):
        if isinstance(item, Spot):
            item = {AxisType.X: item.X,
                    AxisType.Y: item.Y,
                    AxisType.Z: item.Z}
            super().appendleft(item)
        elif isinstance(item, dict):
            super().appendleft(item)
        else:
            raise ValueError("Invalid frame passed to movement queue.")


class Stage(ABC):
    def __init__(self):
        self.movement_queue = MovementQueue()
        self.on_movement_completed = EventHandler()
        self.on_frame_completed = EventHandler()
        self._axes = {}
        self._connected = False

    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def axes(self) -> Dict[AxisType, Axis]:
        return self._axes

    @abstractmethod
    def stop_all(self):
        for ax in self.axes:
            ax.stop()

    def find_references(self):
        if Settings.get('stage.ref_x'):
            self.axes[AxisType.X].find_reference()
        if Settings.get('stage.ref_y'):
            self.axes[AxisType.Y].find_reference()
        if Settings.get('stage.ref_z'):
            self.axes[AxisType.Z].find_reference()

    @property
    def axes_type(self) -> Type[AxisType]:
        if self._num_channels == 3:
            return AxisType
        else:
            raise ValueError("Not supported channel count.")

    @property
    @abstractmethod
    def _num_channels(self):
        pass

    @abstractmethod
    def trigger_frame(self):
        pass
