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
import queue
import threading
import time

import serial.threaded
import wx
from pubsub import pub

logger = logging.getLogger(__name__)


class ArduTrigger(serial.threaded.LineReader):
    TERMINATOR = b"\n"

    def __init__(self) -> None:
        super(ArduTrigger, self).__init__()
        self.alive = True
        self.responses = queue.Queue[str]()
        self.lock = threading.Lock()
        self._awaiting_response_for: str | None = None
        self.cease_continuous_run = threading.Event()
        self.stop_done_event = threading.Event()
        self.rep_sleep_time = 0
        self.rep_count = 1
        self.events = queue.Queue[str | None]()
        self._event_thread = threading.Thread(target=self._run_event)
        self._event_thread.daemon = True
        self._event_thread.name = "at-event"
        self._event_thread.start()
        self.done = False
        self.send_done_msg = False

    def stop(self) -> None:
        """
        Stop the event processing thread, abort pending commands, if any.
        """
        self.alive = False
        self.events.put(None)
        self.responses.put("<exit>")  # TODO: ??

    def _run_event(self) -> None:
        """
        Process events in a separate thread so that input thread is not
        blocked.
        """
        while self.alive:
            try:
                self.handle_event(self.events.get())
            except:
                pass

    def handle_line(self, line: str) -> None:
        """
        Handle input from serial port, check for events.
        """
        if line.startswith("D") or line.startswith("S"):
            self.events.put(line)
        else:
            self.responses.put(line)

    def handle_event(self, event: str | None) -> None:
        """Handle events"""
        if event is None:
            return

        if event == "D":
            time.sleep(self.rep_sleep_time / 1000)
            self.done = True
            if self.send_done_msg:
                wx.CallAfter(pub.sendMessage, "trigger.done")
        elif event == "S":
            wx.CallAfter(pub.sendMessage, "trigger.step")
            logger.info("Step trigger received")

    def command(self, command: str) -> None:
        """Send a command that doesn't respond"""
        with self.lock:  # ensure that just one thread is sending commands at once
            self.write_line(command)

    def command_with_response(self, command: str) -> str:
        """
        Send a command and wait for the response.
        """
        with self.lock:  # ensure that just one thread is sending commands at once
            self._awaiting_response_for = command
            self.write_line(command)
            response = self.responses.get()
            self._awaiting_response_for = None
            return response

    def set_freq(self, freq: int) -> None:
        self.command("F{}".format(freq))

    def set_count(self, counts: int) -> None:
        self.command("C{}".format(counts))

    def set_first_only(self, on: bool) -> None:
        self.command("O{}".format(1 if on else 0))

    def go(self) -> None:
        logger.info("go")
        self.command("G")

    def go_and_wait(self, cleaning: bool = False, delay_ms: int = 200) -> None:
        logger.info("go_and_wait (cleaning={})".format(cleaning))
        if cleaning:
            self.single_shot()
            time.sleep(delay_ms / 1000)
        self.command("G")
        self.done = False
        while not self.done:
            time.sleep(0.001)

    def single_shot(self) -> None:
        logger.info("single_shot")
        self.command_with_response("I")

    def single_tof(self) -> None:
        self.command_with_response("T")

    def start_trigger(self) -> None:
        self.cease_continuous_run.clear()
        self.stop_done_event.clear()
        self.done = False

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls) -> None:
                counter = 1
                self.command("G")

                while (
                    not self.cease_continuous_run.is_set() and counter < self.rep_count
                ):
                    if self.done:
                        self.go()
                        counter += 1
                        self.done = False

                self.stop_done_event.set()

        continuous_thread = ScheduleThread()
        continuous_thread.start()

    def stop_trigger(self) -> None:
        self.cease_continuous_run.set()
        self.command("S")
        self.done = True
