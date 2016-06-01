from . import api as _api


class ChirpObject(object):
    def __init__(self, handle):
        assert isinstance(handle, _api.Handle)
        self._handle = handle

    def __del__(self):
        if self._handle:
            try:
                self.destroy()
            except:
                pass

    def destroy(self):
        _api.destroy(self._handle)
        self._handle = _api.Handle()

    def tryDestroy(self):
        try:
            self.destroy()
            return True
        except _api.ErrorCode:
            return False

    @property
    def is_alive(self):
        return bool(self._handle)

    @property
    def handle(self):
        return self._handle
