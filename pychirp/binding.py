from . import api as _api
from . import object as _object
import threading as _threading


class _BindingMixin(object):
    def __init__(self):
        self._on_binding_established = None
        self._on_binding_released = None
        self._on_binding_state_changed = None
        self._is_established = False
        self._cv = _threading.Condition()

        _api.asyncGetBindingState(self.handle, self._bindingStateCompletionHandler)

    def _bindingStateCompletionHandler(self, err, is_established):
        if not err:
            with self._cv:
                if self._is_established != is_established:
                    self._is_established = is_established

                    if self._on_binding_state_changed:
                        self._on_binding_state_changed(is_established)

                    fn = self._on_binding_established if is_established else self._on_binding_released
                    if fn:
                        fn()

                    self._cv.notifyAll()
                if self.handle:
                    try:
                        _api.asyncAwaitBindingStateChange(self.handle, self._bindingStateCompletionHandler)
                    except:
                        pass

    @property
    def on_binding_established(self):
        return self._on_binding_established

    @on_binding_established.setter
    def on_binding_established(self, fn):
        self._on_binding_established = fn

    @property
    def on_binding_released(self):
        return self._on_binding_released

    @on_binding_released.setter
    def on_binding_released(self, fn):
        self._on_binding_released = fn

    @property
    def on_binding_state_changed(self):
        return self._on_binding_state_changed

    @on_binding_state_changed.setter
    def on_binding_state_changed(self, fn):
        self._on_binding_state_changed = fn

    @property
    def is_established(self):
        return self._is_established

    def _waitUntilBindingState(self, state):
        with self._cv:
            while self._is_established != state and self.is_alive:
                self._cv.wait()
            if not self.is_alive:
                raise Exception('The object has been destroyed')

    def waitUntilEstablished(self):
        self._waitUntilBindingState(True)

    def waitUntilReleased(self):
        self._waitUntilBindingState(False)

    def destroy(self):
        super(_BindingMixin, self).destroy()
        with self._cv:
            self._cv.notifyAll()

    def tryDestroy(self):
        if not super(_BindingMixin, self).tryDestroy():
            return False
        with self._cv:
            self._cv.notifyAll()
        return True


class Binding(_BindingMixin, _object.ChirpObject):
    def __init__(self, terminal, targets):
        from .terminals import _ManualBindTerminal
        assert isinstance(terminal, _ManualBindTerminal)
        assert isinstance(targets, str)
        self._terminal = terminal
        self._targets = targets
        _object.ChirpObject.__init__(self, _api.createBinding(terminal.handle, targets.encode()))
        _BindingMixin.__init__(self)

    @property
    def terminal(self):
        return self._terminal

    @property
    def targets(self):
        return self._targets
