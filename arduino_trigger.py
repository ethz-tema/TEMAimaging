import threading

import serial
import time


class ArduinoTrigger:
    def __init__(self):
        self.conn = serial.Serial('/dev/ttyACM0', timeout=None)
        self.cease_continuous_run = threading.Event()
        self.done_event = threading.Event()
        self.stop_done_event = threading.Event()
        self.rep_sleep_time = 0
        self.rep_count = 1

    def set_freq(self, freq):
        self.conn.write('F{}\n'.format(freq).encode('ASCII'))

    def set_count(self, counts):
        self.conn.write('C{}\n'.format(counts).encode('ASCII'))

    def start(self):
        self.cease_continuous_run.clear()
        self.stop_done_event.clear()
        self.done_event.clear()

        class DonePollingThread(threading.Thread):
            @classmethod
            def run(cls):
                while not self.stop_done_event.is_set():
                    if self.conn.readline() == b"D":
                        self.done_event.set()
                        time.sleep(self.rep_sleep_time/1000)
                        self.done_event.clear()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                counter = 1
                self.conn.write(b'G\n')

                while not self.cease_continuous_run.is_set() and counter < self.rep_count:
                    if self.done_event.is_set():
                        self.conn.write(b'G\n')
                        counter += 1

                self.stop_done_event.set()

        done_polling_thread = DonePollingThread()
        done_polling_thread.start()

        continuous_thread = ScheduleThread()
        continuous_thread.start()

    def stop(self):
        self.cease_continuous_run.set()
        self.conn.write(b'S\n')


arduino = ArduinoTrigger()
