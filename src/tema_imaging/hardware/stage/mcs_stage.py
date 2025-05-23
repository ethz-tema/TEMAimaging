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

import logging
import threading
from enum import IntEnum

from cffi import FFI, error

from tema_imaging.core.settings import Settings
from tema_imaging.core.utils import get_project_root
from tema_imaging.hardware.stage import (
    Axis,
    AxisMovementMode,
    AxisStatus,
    AxisType,
    Stage,
    StageError,
)
from tema_imaging.hardware.utils import StatusPoller


class SAError(IntEnum):
    SA_OK = 0
    SA_INITIALIZATION_ERROR = 1
    SA_NOT_INITIALIZED_ERROR = 2
    SA_NO_SYSTEMS_FOUND_ERROR = 3
    SA_TOO_MANY_SYSTEMS_ERROR = 4
    SA_INVALID_SYSTEM_INDEX_ERROR = 5
    SA_INVALID_CHANNEL_INDEX_ERROR = 6
    SA_TRANSMIT_ERROR = 7
    SA_WRITE_ERROR = 8
    SA_INVALID_PARAMETER_ERROR = 9
    SA_READ_ERROR = 10
    SA_INTERNAL_ERROR = 12
    SA_WRONG_MODE_ERROR = 13
    SA_PROTOCOL_ERROR = 14
    SA_TIMEOUT_ERROR = 15
    SA_ID_LIST_TOO_SMALL_ERROR = 17
    SA_SYSTEM_ALREADY_ADDED_ERROR = 18
    SA_WRONG_CHANNEL_TYPE_ERROR = 19
    SA_CANCELED_ERROR = 20
    SA_INVALID_SYSTEM_LOCATOR_ERROR = 21
    SA_INPUT_BUFFER_OVERFLOW_ERROR = 22
    SA_QUERYBUFFER_SIZE_ERROR = 23
    SA_DRIVER_ERROR = 24
    SA_NO_SENSOR_PRESENT_ERROR = 129
    SA_AMPLITUDE_TOO_LOW_ERROR = 130
    SA_AMPLITUDE_TOO_HIGH_ERROR = 131
    SA_FREQUENCY_TOO_LOW_ERROR = 132
    SA_FREQUENCY_TOO_HIGH_ERROR = 133
    SA_SCAN_TARGET_TOO_HIGH_ERROR = 135
    SA_SCAN_SPEED_TOO_LOW_ERROR = 136
    SA_SCAN_SPEED_TOO_HIGH_ERROR = 137
    SA_SENSOR_DISABLED_ERROR = 140
    SA_COMMAND_OVERRIDDEN_ERROR = 141
    SA_END_STOP_REACHED_ERROR = 142
    SA_WRONG_SENSOR_TYPE_ERROR = 143
    SA_COULD_NOT_FIND_REF_ERROR = 144
    SA_WRONG_END_EFFECTOR_TYPE_ERROR = 145
    SA_MOVEMENT_LOCKED_ERROR = 146
    SA_RANGE_LIMIT_REACHED_ERROR = 147
    SA_PHYSICAL_POSITION_UNKNOWN_ERROR = 148
    SA_OUTPUT_BUFFER_OVERFLOW_ERROR = 149
    SA_COMMAND_NOT_PROCESSABLE_ERROR = 150
    SA_WAITING_FOR_TRIGGER_ERROR = 151
    SA_COMMAND_NOT_TRIGGERABLE_ERROR = 152
    SA_COMMAND_QUEUE_FULL_ERROR = 153
    SA_INVALID_COMPONENT_ERROR = 154
    SA_INVALID_SUB_COMPONENT_ERROR = 155
    SA_INVALID_PROPERTY_ERROR = 156
    SA_PERMISSION_DENIED_ERROR = 157
    SA_UNKNOWN_COMMAND_ERROR = 240
    SA_OTHER_ERROR = 255


class SAHCMMode(IntEnum):
    SA_HCM_DISABLED = 0
    SA_HCM_ENABLED = 1
    SA_HCM_CONTROLS_DISABLED = 2


class SAChannelStatus(IntEnum):
    SA_STOPPED_STATUS = 0
    SA_STEPPING_STATUS = 1
    SA_SCANNING_STATUS = 2
    SA_HOLDING_STATUS = 3
    SA_TARGET_STATUS = 4
    SA_MOVE_DELAY_STATUS = 5
    SA_CALIBRATING_STATUS = 6
    SA_FINDING_REF_STATUS = 7
    SA_OPENING_STATUS = 8


class SAFindRefMarkDirection(IntEnum):
    SA_FORWARD_DIRECTION = 0
    SA_BACKWARD_DIRECTION = 1
    SA_FORWARD_BACKWARD_DIRECTION = 2
    SA_BACKWARD_FORWARD_DIRECTION = 3
    SA_FORWARD_DIRECTION_ABORT_ON_ENDSTOP = 4
    SA_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP = 5
    SA_FORWARD_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP = 6
    SA_BACKWARD_FORWARD_DIRECTION_ABORT_ON_ENDSTOP = 7


class MCSError(StageError):
    def __init__(self, status: SAError) -> None:
        self.status = status


ffi = FFI()
try:
    ffi.cdef(
        open(get_project_root() / "src/tema_imaging/hardware/mcs.cdef", "r").read()
    )
    lib = ffi.dlopen("libmcscontrol.so")
except error.FFIError:
    pass
except error.CDefError:
    pass
except OSError:
    pass

logger = logging.getLogger(__name__)


def check_return(status: SAError) -> bool:
    if status != SAError.SA_OK:
        raise MCSError(SAError(status))
    else:
        return True


class MCSStage(Stage):
    @classmethod
    def find_systems(cls) -> list[str]:
        out = ffi.new("char[4096]")
        out_size = ffi.new("unsigned int *", ffi.sizeof(out))
        if check_return(lib.SA_FindSystems(b"", out, out_size)):
            return ffi.unpack(out, out_size[0]).split("\n")

    def __init__(self, conn_id: str) -> None:
        super().__init__()
        self.id = conn_id
        self.handle = None
        self.status_poller_thread = MCSStage.PollThread(self)
        self.check_movement = threading.Event()
        self._frame_triggered = False

    def connect(self) -> None:
        if not self._connected:
            handle = ffi.new("SA_INDEX *")
            locator = str(self.id).encode("ASCII")

            if check_return(lib.SA_OpenSystem(handle, locator, b"sync")):
                self.handle = handle[0]
                self._connected = True
                logger.info("Connected. axes type: {}".format(self.axes_type))
                for ax in self.axes_type:
                    self._axes[ax] = MCSAxis(ax.name, ax.value, self)
                self.status_poller_thread.start()
            else:
                self._connected = False

    def disconnect(self) -> None:
        if self._connected:
            self.status_poller_thread.stop()
            if check_return(lib.SA_CloseSystem(self.handle)):
                self._connected = False
                self.handle = None

    def set_hcm_mode(self, mode: bool) -> None:
        if self._connected:
            check_return(lib.SA_SetHCMEnabled(self.handle, mode))

    @property
    def _num_channels(self) -> int:
        if self._connected:
            ch = ffi.new("unsigned int *")
            if check_return(lib.SA_GetNumberOfChannels(self.handle, ch)):
                return ch[0]

    def find_references(self) -> None:
        if Settings.get("stage.ref_x"):
            self.axes[AxisType.X].find_reference()
        if Settings.get("stage.ref_y"):
            self.axes[AxisType.Y].find_reference()
        if Settings.get("stage.ref_z"):
            self.axes[AxisType.Z].find_reference()

    def stop_all(self) -> None:
        self.movement_queue.clear()
        for ax in self.axes.values():
            ax.stop()

    def trigger_frame(self) -> None:
        frame = self.movement_queue.pop()
        for axis, v in frame.items():
            if v is not None:
                self.axes[axis].move(v, False)
        self.commit_move()
        self._frame_triggered = True

    class PollThread(StatusPoller):
        def __init__(self, stage: "MCSStage") -> None:
            super().__init__()
            self.stage = stage

        def run(self) -> None:
            statuses = {}
            while not self._run.is_set():
                self.stage.check_movement.wait()
                for a in self.stage._axes.values():
                    if a.moved:
                        if a.status == AxisStatus.STOPPED:
                            a.reset_moved()
                            statuses[a] = True
                        else:
                            statuses[a] = False
                if statuses:
                    if all(statuses.values()):
                        logger.debug("Waited for: {}".format(statuses.keys()))
                        self.stage.on_movement_completed()
                        if self.stage._frame_triggered:
                            self.stage.on_frame_completed()
                            self.stage._frame_triggered = False
                        statuses.clear()
                        self.stage.check_movement.clear()
                else:
                    self.stage.check_movement.clear()

        def stop(self) -> None:
            self._run.set()
            self.stage.check_movement.set()
            self.join()

    def commit_move(self) -> None:
        self.check_movement.set()


class MCSAxis(Axis):
    _channel_status_map = {
        SAChannelStatus.SA_STOPPED_STATUS: AxisStatus.STOPPED,
        SAChannelStatus.SA_STEPPING_STATUS: AxisStatus.MOVING,
        SAChannelStatus.SA_SCANNING_STATUS: AxisStatus.MOVING,
        SAChannelStatus.SA_HOLDING_STATUS: AxisStatus.STOPPED,
        SAChannelStatus.SA_TARGET_STATUS: AxisStatus.MOVING,
        SAChannelStatus.SA_MOVE_DELAY_STATUS: AxisStatus.WAITING,
        SAChannelStatus.SA_CALIBRATING_STATUS: AxisStatus.MOVING,
        SAChannelStatus.SA_FINDING_REF_STATUS: AxisStatus.MOVING,
        SAChannelStatus.SA_OPENING_STATUS: AxisStatus.MOVING,
    }

    def __init__(self, name: str, channel: int, stage: "MCSStage") -> None:
        super().__init__(name, channel)
        self._movement_mode = None
        self._moved = False
        self._stage = stage

    def move(self, value: int, auto_commit: bool = True) -> None:
        position = int(value)
        logger.debug(
            "[move] Channel: {}, Value: {}, Mode: {}".format(
                self._channel, value, self.movement_mode
            )
        )
        if self._stage.handle:
            if self.movement_mode == AxisMovementMode.CL_RELATIVE and value != 0:
                check_return(
                    lib.SA_GotoPositionRelative_S(
                        self._stage.handle, self._channel, position, 0
                    )
                )
                self._moved = True
                if auto_commit:
                    self._stage.check_movement.set()
            elif self.movement_mode == AxisMovementMode.CL_ABSOLUTE:
                check_return(
                    lib.SA_GotoPositionAbsolute_S(
                        self._stage.handle, self._channel, position, 0
                    )
                )
                self._moved = True
                if auto_commit:
                    self._stage.check_movement.set()
            else:
                raise ValueError(
                    "Invalid movement mode ({}) specified.".format(self.movement_mode)
                )

    def stop(self) -> None:
        logger.debug("[stop] Channel: {}".format(self._channel))
        if self._stage.handle:
            check_return(lib.SA_Stop_S(self._stage.handle, self._channel))
            self._moved = False

    def find_reference(self) -> None:
        if self._stage.handle and not self.is_referenced:
            check_return(
                lib.SA_FindReferenceMark_S(
                    self._stage.handle,
                    self._channel,
                    SAFindRefMarkDirection.SA_BACKWARD_FORWARD_DIRECTION,
                    0,
                    1,
                )
            )
            self._moved = True
            self._stage.check_movement.set()

    @property
    def is_referenced(self) -> bool:
        if self._stage.handle:
            known = ffi.new("unsigned int *")
            lib.SA_GetPhysicalPositionKnown_S(self._stage.handle, self._channel, known)
            return bool(known[0])
        else:
            return False

    @property
    def position(self) -> int:
        if self._stage.handle:
            pos = ffi.new("int *")
            check_return(lib.SA_GetPosition_S(self._stage.handle, self._channel, pos))
            return pos[0]

    @property
    def speed(self) -> int:
        if self._stage.handle:
            speed = ffi.new("unsigned int *")
            lib.SA_GetClosedLoopMoveSpeed_S(self._stage.handle, self._channel, speed)
            return speed[0]

    @speed.setter
    def speed(self, value: float) -> None:
        value = int(value)
        logger.info(
            "[speed.setter] Channel: {}, Speed: {}".format(self._channel, value)
        )
        if self._stage.handle:
            check_return(
                lib.SA_SetClosedLoopMoveSpeed_S(
                    self._stage.handle, self._channel, value
                )
            )

    @property
    def position_limit(self) -> tuple[int, int]:
        if self._stage.handle:
            min_limit = ffi.new("int *")
            max_limit = ffi.new("int *")
            check_return(
                lib.SA_GetPositionLimit_S(
                    self._stage.handle, self._channel, min_limit, max_limit
                )
            )

            return min_limit[0], max_limit[0]

    @position_limit.setter
    def position_limit(self, value: tuple[int, int]):
        if (
            self._stage.handle and self.is_referenced
        ):  # TODO: raise Error if not referenced?
            check_return(
                lib.SA_SetPositionLimit_S(
                    self._stage.handle, self._channel, value[0], value[1]
                )
            )

    @property
    def movement_mode(self) -> AxisMovementMode:
        return self._movement_mode

    @movement_mode.setter
    def movement_mode(self, value: AxisMovementMode):
        self._movement_mode = value

    @property
    def status(self) -> AxisStatus:
        if self._stage.handle:
            s = ffi.new("unsigned int *")
            check_return(lib.SA_GetStatus_S(self._stage.handle, self._channel, s))
            return MCSAxis._channel_status_map[SAChannelStatus(s[0])]

    @property
    def moved(self) -> bool:
        return self._moved

    def reset_moved(self) -> None:
        self._moved = False
