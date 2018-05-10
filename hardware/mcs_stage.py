import logging
from enum import IntEnum

from cffi import FFI, error


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


class MCSAxis(IntEnum):
    X = 0
    Y = 1
    Z = 2


class MCSError(Exception):
    def __init__(self, status):
        self.status = status


ffi = FFI()
try:
    ffi.cdef(open('hardware/mcs.cdef', 'r').read())
    lib = ffi.dlopen('libmcscontrol.so')
except error.FFIError:
    pass
except error.CDefError:
    pass

logger = logging.getLogger(__name__)


class MCSStage:
    @staticmethod
    def check_return(status):
        if status != SAError.SA_OK:
            raise MCSError(SAError(status))
        else:
            return True

    @classmethod
    def find_systems(cls):
        out = ffi.new('char[4096]')
        out_size = ffi.new('unsigned int *', ffi.sizeof(out))
        if cls.check_return(lib.SA_FindSystems(b'', out, out_size)):
            return ffi.unpack(out, out_size[0]).split('\n')

    def __init__(self, conn_id):
        self.id = conn_id
        self.handle = 0
        self.is_open = False
        self._num_channels = None

    def open_mcs(self):
        if not self.is_open:
            handle = ffi.new('SA_INDEX *')
            locator = str(self.id).encode('ASCII')

            if self.check_return(lib.SA_OpenSystem(handle, locator, b'sync')):
                self.handle = handle[0]
                self.is_open = True
            else:
                self.is_open = False

    def close_mcs(self):
        if self.is_open:
            if self.check_return(lib.SA_CloseSystem(self.handle)):
                self.is_open = False

    def get_axis_status(self, axis):
        if self.is_open:
            s = ffi.new('unsigned int *')
            self.check_return(lib.SA_GetStatus_S(self.handle, axis, s))
            return s[0]

    def wait_until_status(self, axes=None, status=SAChannelStatus.SA_STOPPED_STATUS):
        if axes is None:
            axes = [MCSAxis.X, MCSAxis.Y, MCSAxis.Z]
        statuses = {}
        while True:
            for a in axes:
                statuses[a] = self.get_axis_status(a) == status
            if all(statuses.values()):
                return

    def set_hcm_mode(self, mode):
        if self.is_open:
            self.check_return(lib.SA_SetHCMEnabled(self.handle, mode))

    @property
    def num_channels(self):
        if self._num_channels is not None:
            return self._num_channels

        if self.is_open:
            ch = ffi.new('unsigned int *')
            if self.check_return(lib.SA_GetNumberOfChannels(self.handle, ch)):
                self._num_channels = ch[0]
                return self._num_channels

    def get_position_limit(self, axis):
        if self.is_open:
            min_limit = ffi.new('int *')
            max_limit = ffi.new('int *')
            self.check_return(lib.SA_GetPositionLimit_S(self.handle, axis, min_limit, max_limit))

            return min_limit[0], max_limit[0]

    def set_position_limit(self, axis, min_limit, max_limit):
        if self.is_open:
            if self.get_position_known(axis):
                self.check_return(lib.SA_SetPositionLimit_S(self.handle, axis, min_limit, max_limit))

    def find_reference(self, axis, hold_time=0):
        if self.is_open:
            if not self.get_position_known(axis):
                self.check_return(
                    lib.SA_FindReferenceMark_S(self.handle, axis, SAFindRefMarkDirection.SA_BACKWARD_FORWARD_DIRECTION,
                                               hold_time, 1))

    def find_references(self, hold_time=0):
        for a in MCSAxis:
            self.find_reference(a, hold_time)

        self.wait_until_status()

    def get_position_known(self, axis=None):
        if axis is None:
            return [self.get_position_known(axis) for axis in MCSAxis]

        if self.is_open:
            known = ffi.new('unsigned int *')
            lib.SA_GetPhysicalPositionKnown_S(self.handle, axis, known)
            return known[0]

    def get_position(self, axis=None):
        if axis is None:
            return [self.get_position(axis) for axis in MCSAxis]

        if self.is_open:
            pos = ffi.new('int *')
            self.check_return(lib.SA_GetPosition_S(self.handle, axis, pos))
            return pos[0] / 1e9

    def get_speed(self, axis=None):
        if axis is None:
            for a in MCSAxis:
                self.get_speed(a)

        if self.is_open:
            speed = ffi.new('unsigned int *')
            lib.SA_GetClosedLoopMoveSpeed_S(self.handle, axis, speed)
            return speed[0] / 1e9

    def set_speed(self, speed, axis=None):
        speed = int(speed * 1e9)
        if axis is None:
            for a in MCSAxis:
                self.set_speed(speed, a)
            return

        logger.info('set_speed (axis={}, speed={})'.format(axis, speed))
        if self.is_open:
            self.check_return(lib.SA_SetClosedLoopMoveSpeed_S(self.handle, int(axis), int(speed)))

    def move(self, axis, position, hold_time=0, relative=False, wait=True):
        logger.info('move (axis={}, pos={}, relative={}, wait={}'.format(axis, position, relative, wait))
        position = int(position * 1e9)
        if self.is_open:
            if relative:
                self.check_return(lib.SA_GotoPositionRelative_S(self.handle, axis, position, hold_time))
            else:
                self.check_return(lib.SA_GotoPositionAbsolute_S(self.handle, axis, position, hold_time))

            if wait:
                self.wait_until_status([axis])

# stage = MCSStage('usb:ix:0')

# stage.open_mcs()
# stage.find_references()

# stage.set_position_limit(MCSAxis.X, -25000000, 25000000)
# stage.set_position_limit(MCSAxis.Y, -34000000, 35000000)
# stage.set_position_limit(MCSAxis.Z, -750000, 2700000)

# for i in range(5):
#    stage.move(MCSAxis.X, 100000, relative=True)

# stage.close_mcs()

# for i in range(3):
#    error = lib.SA_SetClosedLoopMoveSpeed_S(mcs_handle[0], i, 20000000)
#    print(SAError(error))
# lib.SA_SetClosedLoopMoveAcceleration_S(mcs_handle[0], i, 0)
