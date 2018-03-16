import enum
import threading

import serial


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


class Trigger(enum.Enum):
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
