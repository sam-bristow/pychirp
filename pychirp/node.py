from . import api as _api
from . import object as _object
from . import scheduler as _scheduler


class Node(_object.ChirpObject):
    def __init__(self, scheduler):
        assert isinstance(scheduler, _scheduler.Scheduler)
        self._scheduler = scheduler
        super(Node, self).__init__(_api.createNode(scheduler.handle))

    @property
    def scheduler(self):
        return self._scheduler

    def getKnownTerminals(self):
        return _api.getKnownTerminals(self._handle)

    def asyncAwaitKnownTerminalsChange(self, completion_handler):
        _api.asyncAwaitKnownTerminalsChange(self._handle, completion_handler)

    def cancelAwaitKnownTerminalsChange(self):
        _api.cancelAwaitKnownTerminalsChange(self._handle)
