import logging
import threading

import arduino_trigger
import laser_compex
from mcs_stage import MCSStage, MCSError


class MeasurementController:
    def __init__(self, laser, trigger, stage):
        self.laser = laser  # type: laser_compex.CompexLaserProtocol
        self.trigger = trigger  # type: arduino_trigger.ArduTrigger
        self.stage = stage  # type: MCSStage

    def start_scan(self, scan):
        scan.set_instruments(self.laser, self.trigger, self.stage)
        stop_scan = threading.Event()

        class MeasureThread(threading.Thread):
            @classmethod
            def run(cls):
                try:
                    while scan.next_move() and not stop_scan.is_set():
                        scan.next_shot()
                except MCSError as e:
                    logging.exception(e)

        thread = MeasureThread()
        thread.start()

        return stop_scan
