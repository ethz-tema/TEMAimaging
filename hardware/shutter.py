from AIOUSB import *

MAX_DIO_BYTES = 32


class ShutterException(Exception):
    pass


class Shutter:
    def __init__(self, dev, output):
        self.io_device = dev
        self.output = output

    def open(self):
        self.io_device.set_output(self.output, True)

    def close(self):
        self.io_device.set_output(self.output, False)

    def set(self, _open=False):
        self.io_device.set_output(self.output, _open)

    @property
    def status(self):
        return self.io_device.get_output(self.output)


class AIODevice:
    def __init__(self, index=0):
        self.index = index
        self.curr_status = DIOBuf(MAX_DIO_BYTES)
        self.output_mask = NewAIOChannelMaskFromStr("0001")  # Channels A are used as outputs
        self._connected = False

    def connect(self):
        result = AIOUSB_Init()
        if result != AIOUSB_SUCCESS or AIOUSB_EnsureOpen(self.index) != AIOUSB_SUCCESS:
            self._connected = False
            raise ShutterException(result)
        self._connected = True

        DIO_ReadAllToDIOBuf(self.index, self.curr_status)

    def disconnect(self):
        AIOUSB_Exit()
        self._connected = False

    def set_output(self, output, on):
        if self._connected:
            DIOBufSetIndex(self.curr_status, output, 1 if on else 0)
            DIO_ConfigureWithDIOBuf(self.index, AIOUSB_FALSE, self.output_mask, self.curr_status)

    def get_output(self, output):
        if self._connected:
            DIO_ReadAllToDIOBuf(self.index, self.curr_status)
            return DIOBufGetIndex(self.curr_status, output)
