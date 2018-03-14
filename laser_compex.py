import enum
import threading

import serial


class OpMode(enum.Enum):
    OFF = 'OFF'
    OFF_WAIT = 'OFF,WAIT'
    ON = 'ON'


class Trigger(enum.Enum):
    INT = 'INT'
    EXT = 'EXT'


class StatusCodes(enum.IntEnum):
    NO_MSG_OR_WARN_OR_INTERLOCK = 0
    INTERLOCK = 1
    WARM_UP = 21
    LOW_LIGHT = 26
    COD_ON = 36


class CompexLaser:
    def __init__(self):
        self.conn = serial.Serial('/dev/ttyUSB0', timeout=0.5)
        self.lock = threading.Lock()

    def _safe_set(self, cmd):
        self.lock.acquire()
        try:
            self.conn.write(cmd.encode('ASCII'))
        finally:
            self.lock.release()

    def _safe_get(self, cmd):
        self.lock.acquire()
        try:
            self.conn.write(cmd.encode('ASCII'))
            return self.conn.readline().decode()[:-1]
        finally:
            self.lock.release()

    @property
    def opmode(self):
        data = self._safe_get('OPMODE?\r').split(':')

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
        self._safe_set('OPMODE={}\r'.format(mode.value))

    @property
    def trigger(self):
        data = self._safe_get('TRIGGER?\r')

        try:
            return Trigger(data)
        except ValueError:
            return None

    @property
    def reprate(self):
        return int(self._safe_get('REPRATE?\r'))

    @reprate.setter
    def reprate(self, rate):
        self._safe_set('REPRATE={}\r'.format(rate))

    @property
    def counts(self):
        return self._safe_get('COUNTS?\r')

    @counts.setter
    def counts(self, counts):
        self._safe_set('COUNTS={}\r'.format(counts))

    @trigger.setter
    def trigger(self, mode):
        self._safe_set('TRIGGER={}\r'.format(mode.value))

    @property
    def laser_type(self):
        return self._safe_get('TYPE OF LASER?\r')

    @property
    def version(self):
        return self._safe_get('VERSION?\r')


laser = CompexLaser()
