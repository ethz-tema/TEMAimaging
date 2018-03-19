from cffi import FFI
import time
from enum import IntEnum


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


class SAHCMStatus(IntEnum):
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


class MCSError(Exception):
    def __init__(self, status):
        self.status = status


class MCSStage:
    @staticmethod
    def check_return(status):
        if status != SAError.SA_OK:
            raise MCSError(status)
        else:
            return True

    @classmethod
    def find_systems(cls):
        out = ffi.new('char[4096]')
        out_size = ffi.new('unsigned int *', ffi.sizeof(out))
        if cls.check_return(lib.SA_FindSystems(b'', out, out_size)):
            return ffi.unpack(out, out_size[0])


ffi = FFI()
ffi.cdef(open('mcs.cdef', 'r').read())

lib = ffi.dlopen('libmcscontrol.so')



version = ffi.new('unsigned int *')
lib.SA_GetDLLVersion(version)
print('Version: {}'.format(version[0]))

mcs_handle = ffi.new('SA_INDEX *')
locator = 'usb:ix:0'.encode('ASCII')
options = 'sync'.encode('ASCII')

error = lib.SA_OpenSystem(mcs_handle, locator, options)
if error:
    print("Error OpenSystem: {}".format(SAError(error)))

num_channels = ffi.new('unsigned int *')
error = lib.SA_GetNumberOfChannels(mcs_handle[0], num_channels)
print('Number of channels: {}'.format(num_channels[0]))

ch_type = ffi.new('unsigned int *')
for i in range(3):
    error = lib.SA_GetChannelType(mcs_handle[0], i, ch_type)
    if error:
        print(SAError(error))
        continue
    print('Channel {} Type: {}'.format(i, ch_type[0]))

known = ffi.new('unsigned int *')
lib.SA_GetPhysicalPositionKnown_S(mcs_handle[0], 0, known)
print('Known: {}'.format(known[0]))
if not known[0]:
    error = lib.SA_FindReferenceMark_S(mcs_handle[0], 0, 0, 5000, 1)
    print(SAError(error))
    lib.SA_FindReferenceMark_S(mcs_handle[0], 1, 0, 5000, 1)
    print(SAError(error))
    lib.SA_FindReferenceMark_S(mcs_handle[0], 2, 0, 5000, 1)
    print(SAError(error))
    status = ffi.new('unsigned int *')
    lib.SA_GetStatus_S(mcs_handle[0], 0, status)
    while status[0] == SAChannelStatus.SA_FINDING_REF_STATUS:
        lib.SA_GetStatus_S(mcs_handle[0], 0, status)
        time.sleep(0.1)

error = lib.SA_SetPositionLimit_S(mcs_handle[0], 0, -25000000, 25000000)
print(SAError(error))
error = lib.SA_SetPositionLimit_S(mcs_handle[0], 1, -34000000, 35000000)
print(SAError(error))
error = lib.SA_SetPositionLimit_S(mcs_handle[0], 2, -750000, 2700000)
print(SAError(error))

for i in range(3):
    error = lib.SA_SetClosedLoopMoveSpeed_S(mcs_handle[0], i, 20000000)
    print(SAError(error))
    #lib.SA_SetClosedLoopMoveAcceleration_S(mcs_handle[0], i, 0)


#lib.SA_SetHCMEnabled(mcs_handle[0], SAHCMStatus.SA_HCM_ENABLED)

#for i in range(0):
#    lib.SA_GotoPositionRelative_S(mcs_handle[0], 0, 1000000, 0)
#    lib.SA_GotoPositionRelative_S(mcs_handle[0], 1, 1000000, 0)
#    lib.SA_GotoPositionRelative_S(mcs_handle[0], 2, 500000, 0)

lib.SA_GotoPositionAbsolute_S(mcs_handle[0], 0, 4000000, 10000)
lib.SA_GotoPositionAbsolute_S(mcs_handle[0], 1, -2537744, 10000)
error = lib.SA_GotoPositionAbsolute_S(mcs_handle[0], 2, 5000000, 10000)
print(SAError(error))


status = ffi.new('unsigned int *')
position = ffi.new('int *')
lib.SA_GetStatus_S(mcs_handle[0], 0, status)
lib.SA_GetPosition_S(mcs_handle[0], 0, position)
print('Position: {} nm'.format(position[0]))

while status[0] == 4:
    time.sleep(0.05)
    lib.SA_GetStatus_S(mcs_handle[0], 0, status)

    lib.SA_GetPosition_S(mcs_handle[0], 0, position)
    print('Position: {} nm'.format(position[0]))

lib.SA_CloseSystem(mcs_handle[0])