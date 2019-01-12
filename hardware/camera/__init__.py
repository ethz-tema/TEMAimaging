from threading import Thread


class CameraThread(Thread):
    def __init__(self, camera, notify, timeout=100):
        super(CameraThread, self).__init__()
        self.alive = True
        self.camera = camera
        self.notify = notify
        self.timeout = timeout

    def run(self):
        while self.alive:
            # ignore image transfer errors
            try:
                image = self.camera.get_frame()
                self.notify(self.camera, image)
            except CameraException as e:
                if e.fatal:
                    raise e

    def stop(self):
        self.alive = False
        self.join()


class CameraException(Exception):
    def __init__(self, fatal):
        self.fatal = fatal
