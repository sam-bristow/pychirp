from . import api as _api
from . import object as _object
from . import scheduler as _scheduler


class Leaf(_object.ChirpObject):
    def __init__(self, scheduler):
        assert isinstance(scheduler, _scheduler.Scheduler)
        self._scheduler = scheduler
        super(Leaf, self).__init__(_api.createLeaf(scheduler.handle))

    @property
    def scheduler(self):
        return self._scheduler
