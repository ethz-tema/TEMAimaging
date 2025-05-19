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

try:
    from AIOUSB import *
except ImportError:
    pass

MAX_DIO_BYTES = 32


class ShutterException(Exception):
    pass


class Shutter:
    def __init__(self, dev: 'AIODevice', output: int) -> None:
        self.io_device = dev
        self.output = output

    def open(self) -> None:
        self.io_device.set_output(self.output, True)

    def close(self) -> None:
        self.io_device.set_output(self.output, False)

    def set(self, open_: bool = False) -> None:
        self.io_device.set_output(self.output, open_)

    @property
    def status(self) -> bool:
        return self.io_device.get_output(self.output)


class AIODevice:
    def __init__(self, index: int = 0) -> None:
        self.index = index
        self.curr_status = DIOBuf(MAX_DIO_BYTES)
        self.output_mask = NewAIOChannelMaskFromStr("0001")  # Channels A are used as outputs
        self._connected = False

    def connect(self) -> None:
        result = AIOUSB_Init()
        if result != AIOUSB_SUCCESS or AIOUSB_EnsureOpen(self.index) != AIOUSB_SUCCESS:
            self._connected = False
            raise ShutterException(result)
        self._connected = True

        DIO_ReadAllToDIOBuf(self.index, self.curr_status)

    def disconnect(self) -> None:
        AIOUSB_Exit()
        self._connected = False

    def set_output(self, output: int, on: bool) -> None:
        if self._connected:
            DIOBufSetIndex(self.curr_status, output, 1 if on else 0)
            DIO_ConfigureWithDIOBuf(self.index, AIOUSB_FALSE, self.output_mask, self.curr_status)

    def get_output(self, output: int) -> bool:
        if self._connected:
            DIO_ReadAllToDIOBuf(self.index, self.curr_status)
            return DIOBufGetIndex(self.curr_status, output)
