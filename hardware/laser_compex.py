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

import enum
import logging
import queue
import threading

import serial.threaded


class OpMode(enum.Enum):
    OFF = 'OFF'
    OFF_WAIT = 'OFF,WAIT'
    ON = 'ON'
    SKIP = 'SKIP'
    NEW_FILL = 'NEW FILL'
    PRESERVATION_FILL = 'PRESERVATION FILL'
    PURGE_RESERVOIR = 'PURGE RESERVOIR'
    SAFETY_FILL = 'SAFETY FILL'
    TRANSPORT_FILL = 'TRANSPORT FILL'
    FLUSHING = 'FLUSHING'
    CONT = 'CONT'
    HI = 'HI'
    PGR = 'PGR'
    MANUAL_FILL_INERT = 'MANUAL FILL INERT'
    # FLUSH <xy> LINE
    # PURGE <xy> LINE
    CAPACITY_RESET = 'CAPACITY RESET'
    LL_OFF = 'LL OFF'
    ENERGY_CAL = 'ENERGY CAL'


class TriggerModes(enum.Enum):
    INT = 'INT'
    EXT = 'EXT'


class StatusCodes(enum.IntEnum):
    NO_MSG_OR_WARN_OR_INTERLOCK = 0
    INTERLOCK = 1
    PRESET_ENERGY_TOO_HIGH = 2
    NO_GASFLOW = 3
    WATCHDOG = 4
    FATAL_ERROR = 5
    POLLING = 6
    ENERGY_CAL_ERROR = 7
    NEW_GAS_FILL_NEEDED = 8
    NO_VACUUM = 9
    LOW_PRESSURE = 10
    NO_CAPACITY_LEFT = 11
    ERROR_TEMPERATURE_MEASUREMENT = 12
    FLUORINE_VALVE_NOT_OPEN = 13
    WARM_UP = 21
    LOW_LIGHT = 26
    WRONG_PRESSURE = 27
    MEMORY_MALFUNCTION = 29
    LASER_TUBE_LEAKING = 30
    TIMEOUT = 31
    HALOGEN_PRESSURE_TOO_HIGH = 33
    HI_IN_PREP = 34
    NOT_AVAILABLE = 35
    COD_ON = 36
    REPRATE_FOR_COD_HIGH = 37
    INERT_VALVE_CLOSED = 39
    PRESET_ENERGY_TOO_LOW = 40
    ENTERED_VALUE_TOO_HIGH = 41


class CompexException(Exception):
    pass


class CompexLaserProtocol(serial.threaded.LineReader):
    TERMINATOR = b'\r'

    def __init__(self):
        super(CompexLaserProtocol, self).__init__()
        self.alive = True
        self.responses = queue.Queue()
        self.lock = threading.Lock()
        self._awaiting_response_for = None

        self.connection_lost_cb = None

    def stop(self):
        """
        Stop the event processing thread, abort pending commands, if any.
        """
        self.alive = False
        self.responses.put('<exit>')  # TODO: ??

    def connection_lost(self, exc):
        logging.exception(exc)
        if self.connection_lost_cb:
            self.connection_lost_cb(exc)

    def handle_line(self, line):
        """
        Handle input from serial port, check for events.
        """
        self.responses.put(line)

    def command(self, command):
        """Send a command that doesn't respond"""
        with self.lock:  # ensure that just one thread is sending commands at once
            try:
                self.write_line(command)
            except serial.SerialException as exc:
                self.connection_lost(exc)

    def command_with_response(self, command, response='', timeout=5):
        """
        Set an Compex command and wait for the response.
        """
        with self.lock:  # ensure that just one thread is sending commands at once
            self._awaiting_response_for = command
            self.write_line(command)
            try:
                response = self.responses.get()
            except queue.Empty as e:
                self.connection_lost(e)
            self._awaiting_response_for = None
            return response

    @property
    def opmode(self):
        data = self.command_with_response('OPMODE?')

        data = data.split(':')

        try:
            opmode = OpMode(data[0])
        except ValueError:
            return None, None

        if opmode != OpMode.OFF_WAIT:
            return opmode, StatusCodes(int(data[1]))
        else:
            return opmode, None

    @opmode.setter
    def opmode(self, mode):
        self.command('OPMODE={}'.format(mode.value))

    @property
    def trigger(self):
        data = self.command_with_response('TRIGGER?')

        try:
            return TriggerModes(data)
        except ValueError:
            return None

    @trigger.setter
    def trigger(self, mode):
        self.command('TRIGGER={}'.format(mode.value))

    @property
    def reprate(self):
        return int(self.command_with_response('REPRATE?'))

    @reprate.setter
    def reprate(self, rate):
        self.command('REPRATE={}'.format(rate))

    @property
    def counts(self):
        return int(self.command_with_response('COUNTS?'))

    @counts.setter
    def counts(self, counts):
        self.command('COUNTS={}'.format(counts))

    @property
    def pressure(self):
        return int(self.command_with_response('PRESSURE?'))

    @property
    def tube_temp(self):
        return self.command_with_response('RESERVOIR TEMP?')

    @property
    def tube_temp_control(self):
        return self.command_with_response('TEMP CONTROL?')

    @property
    def hv(self):
        return float(self.command_with_response('HV?'))

    @hv.setter
    def hv(self, hv):
        self.command('HV={:04.1f}'.format(hv))

    @property
    def egy(self):
        return float(self.command_with_response('EGY?'))

    @property
    def cod(self):
        return self.command_with_response('COD?')  # TODO: handle format

    @cod.setter
    def cod(self, cod):
        self.command('COD={}'.format(cod))

    @property
    def filter_contamination(self):
        return int(self.command_with_response('FILTER CONTAMINATION?'))

    def reset_filter_contamination(self):
        self.command('FILTER CONTAMINATION=RESET')

    @property
    def interlock(self):
        return self.command_with_response('INTERLOCK?')  # TODO: handle format

    @property
    def power_stabilization(self):
        return self.command_with_response('POWER STABILIZATION ACHIEVED?')  # TODO: handle format

    @property
    def total_counter(self):
        return int(self.command_with_response('TOTALCOUNTER?'))

    @property
    def laser_type(self):
        return self.command_with_response('TYPE OF LASER?')

    @property
    def version(self):
        return self.command_with_response('VERSION?')
