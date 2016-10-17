from . import api as _api
from . import object as _object
from . import scheduler as _scheduler
from . import terminals as _terminals


class Node(_object.ChirpObject):
    def __init__(self, scheduler):
        assert isinstance(scheduler, _scheduler.Scheduler)
        self._scheduler = scheduler
        super(Node, self).__init__(_api.createNode(scheduler.handle))

    @property
    def scheduler(self):
        return self._scheduler

    def getKnownTerminals(self):
        terminals = _api.getKnownTerminals(self._handle)
        for terminal in terminals:
            terminal['type'] = _terminals.terminalTypeToClass(terminal['type'])
        return terminals

    class TerminalTypes:
        DEAF_MUTE = 0
        PUBLISH_SUBSCRIBE = 1
        SCATTER_GATHER = 2
        CACHED_PUBLISH_SUBSCRIBE = 3
        PRODUCER = 4
        CONSUMER = 5
        CACHED_PRODUCER = 6
        CACHED_CONSUMER = 7
        MASTER = 8
        SLAVE = 9
        CACHED_MASTER = 10
        CACHED_SLAVE = 11
        SERVICE = 12
        CLIENT = 13

    def asyncAwaitKnownTerminalsChange(self, completion_handler):
        def fn(err, info):
            if info:
                info['type'] = _terminals.terminalTypeToClass(info['type'])
            completion_handler(err, info)
        _api.asyncAwaitKnownTerminalsChange(self._handle, fn)

    def cancelAwaitKnownTerminalsChange(self):
        _api.cancelAwaitKnownTerminalsChange(self._handle)
