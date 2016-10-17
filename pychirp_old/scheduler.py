from . import api as _api
from . import object as _object
import atexit as _atexit


class Scheduler(_object.ChirpObject):
    __CHIRP_INITIALISED = False

    @classmethod
    def __initialise_chirp(cls):
        if not cls.__CHIRP_INITIALISED:
            _api.initialise()
            cls.__CHIRP_INITIALISED = True
            _atexit.register(_api.shutdown)

    def __init__(self, num_threads=1):
        Scheduler.__initialise_chirp()
        super(Scheduler, self).__init__(_api.createScheduler())
        try:
            _api.setSchedulerThreadPoolSize(self.handle, num_threads)
        except:
            _api.destroy(self.handle)
            raise

    def setThreadPoolSize(self, num_threads):
        _api.setSchedulerThreadPoolSize(self.handle, num_threads)
