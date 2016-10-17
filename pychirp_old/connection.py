from . import api as _api
from . import object as _object
from . import node as _node
from . import leaf as _leaf


class Connection(_object.ChirpObject):
    def __init__(self, handle):
        super(Connection, self).__init__(handle)
        self._endpoint = None
        try:
            self._description = _api.getConnectionDescription(self.handle)
            self._remote_version = _api.getRemoteVersion(self.handle)
            self._remote_identification = _api.getRemoteIdentification(self.handle)
        except:
            self.destroy()
            raise

    @property
    def description(self):
        return self._description

    @property
    def remote_version(self):
        return self._remote_version

    @property
    def remote_identification(self):
        return self._remote_identification

    @property
    def endpoint(self):
        return self._endpoint

    def assign(self, endpoint, timeout):
        assert isinstance(endpoint, (_leaf.Leaf, _node.Node))
        assert isinstance(timeout, (type(None), float))
        _api.assignConnection(self.handle, endpoint.handle, timeout)
        self._endpoint = endpoint

    def asyncAwaitDeath(self, completion_handler):
        assert hasattr(completion_handler, '__call__')
        _api.asyncAwaitConnectionDeath(self.handle, completion_handler)

    def cancelAwaitDeath(self):
        _api.cancelAwaitConnectionDeath(self.handle)


class LocalConnection(_object.ChirpObject):
    def __init__(self, endpoint_a, endpoint_b):
        assert isinstance(endpoint_a, (_leaf.Leaf, _node.Node))
        assert isinstance(endpoint_b, (_leaf.Leaf, _node.Node))
        self._leaf_or_node_a = endpoint_a
        self._leaf_or_node_b = endpoint_b
        super(LocalConnection, self).__init__(_api.createLocalConnection(endpoint_a.handle, endpoint_b.handle))

    @property
    def endpoint_a(self):
        return self._endpoint_a

    @property
    def endpoint_b(self):
        return self._endpoint_b
