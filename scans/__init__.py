import logging
import threading

from gui.conn_mgr import conn_mgr
from hardware.arduino_trigger import ArduTrigger
from hardware.laser_compex import CompexLaserProtocol
from hardware.mcs_stage import MCSStage, MCSError
from scans.line import LineScan
from scans.rectangle import RectangleScan


class MeasurementController:
    scan_types = {"Line Scan": LineScan, "Rectangle Scan": RectangleScan}

    def __init__(self, laser, trigger, stage):
        self.laser = laser  # type: CompexLaserProtocol
        self.trigger = trigger  # type: ArduTrigger
        self.stage = stage  # type: MCSStage
        self.sequence = []

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

    def init_sequence(self, steps):
        self.sequence.clear()
        for step in steps:
            self.sequence.append(
                step.scan_type.from_params(step.spot_size, step.shots_per_spot, step.frequency, step.cleaning_shot,
                                           step.params))

    def start_sequence(self):
        stop_scan = threading.Event()

        class MeasureThread(threading.Thread):
            @classmethod
            def run(cls):
                try:
                    for scan in self.sequence:
                        scan.set_instruments(conn_mgr.laser, conn_mgr.trigger, conn_mgr.stage)
                        while scan.next_move() and not stop_scan.is_set():
                            scan.next_shot()
                except MCSError as e:
                    logging.exception(e)

        thread = MeasureThread()
        thread.start()

        return stop_scan
