import queue
import threading
import time

import serial.threaded


class ArduinoTriggerProtocol(serial.threaded.LineReader):
    TERMINATOR = b'\n'

    def __init__(self):
        super(ArduinoTriggerProtocol, self).__init__()
        self.alive = True
        self.responses = queue.Queue()
        self.lock = threading.Lock()
        self._awaiting_response_for = None
        self.cease_continuous_run = threading.Event()
        self.stop_done_event = threading.Event()
        self.rep_sleep_time = 0
        self.rep_count = 1
        self.event_responses = queue.Queue()
        self.events = queue.Queue()
        self._event_thread = threading.Thread(target=self._run_event)
        self._event_thread.daemon = True
        self._event_thread.name = 'at-event'
        self._event_thread.start()
        self.done = False

    def stop(self):
        """
        Stop the event processing thread, abort pending commands, if any.
        """
        self.alive = False
        self.events.put(None)
        self.responses.put('<exit>')  # TODO: ??

    def _run_event(self):
        """
        Process events in a separate thread so that input thread is not
        blocked.
        """
        while self.alive:
            try:
                self.handle_event(self.events.get())
            except:
                pass

    def handle_line(self, line):
        """
        Handle input from serial port, check for events.
        """
        if line.startswith('D'):
            self.events.put(line)
        else:
            self.responses.put(line)

    def handle_event(self, event):
        """Handle events"""
        if event == 'D':
            time.sleep(self.rep_sleep_time / 1000)
            self.done = True

    def command(self, command):
        """Send a command that doesn't respond"""
        with self.lock:  # ensure that just one thread is sending commands at once
            self.write_line(command)

    def command_with_response(self, command, response='', timeout=5):
        """
        Set an Compex command and wait for the response.
        """
        with self.lock:  # ensure that just one thread is sending commands at once
            self._awaiting_response_for = command
            self.write_line(command)
            response = self.responses.get()
            self._awaiting_response_for = None
            return response

    def set_freq(self, freq):
        self.command('F{}'.format(freq))

    def set_count(self, counts):
        self.command('C{}'.format(counts))

    def start_trigger(self):
        self.cease_continuous_run.clear()
        self.stop_done_event.clear()
        self.done = False

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                counter = 1
                self.command('G')

                while not self.cease_continuous_run.is_set() and counter < self.rep_count:
                    if self.done:
                        self.command('G')
                        counter += 1
                        self.done = False

                self.stop_done_event.set()

        continuous_thread = ScheduleThread()
        continuous_thread.start()

    def stop_trigger(self):
        self.cease_continuous_run.set()
        self.command('S')
