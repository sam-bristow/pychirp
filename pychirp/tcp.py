from .api import ErrorCodes as _ErrorCodes
from . import connection as _connections
from . import leaf as _leaf
from . import api as _api
from . import object as _object
from . import scheduler as _scheduler
import threading as _threading
import time as _time


def _print(msg):
    print(msg)


def _dummy(*args):
    pass


class TcpServer(_object.ChirpObject):
    def __init__(self, scheduler, address, port, identification=None):
        assert isinstance(scheduler, _scheduler.Scheduler)
        assert isinstance(address, str)
        assert isinstance(port, int)
        assert isinstance(identification, (type(None), bytearray))
        self._scheduler = scheduler
        self._address = address
        self._port = port
        self._identification = identification
        super(TcpServer, self).__init__(_api.createTcpServer(scheduler.handle, address.encode(), port, identification))

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def address(self):
        return self._address

    @property
    def port(self):
        return self._port

    @property
    def identification(self):
        return self._identification

    def asyncAccept(self, handshake_timeout, completion_handler):
        assert isinstance(handshake_timeout, (type(None), float))
        assert hasattr(completion_handler, '__call__')

        def wrappedCompletionHandler(err, connection_handle):
            if connection_handle is None:
                completion_handler(err, None)
            else:
                completion_handler(err, _connections.Connection(connection_handle))

        _api.asyncTcpAccept(self.handle, handshake_timeout, wrappedCompletionHandler)

    def cancelAccept(self):
        _api.cancelTcpAccept(self.handle)


class TcpClient(_object.ChirpObject):
    def __init__(self, scheduler, identification=None):
        assert isinstance(scheduler, _scheduler.Scheduler)
        assert isinstance(identification, (type(None), bytearray))
        self._scheduler = scheduler
        self._identification = identification
        super(TcpClient, self).__init__(_api.createTcpClient(scheduler.handle, identification))

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def identification(self):
        return self._identification

    def asyncConnect(self, host, port, handshake_timeout, completion_handler):
        assert isinstance(host, str)
        assert isinstance(port, int)
        assert isinstance(handshake_timeout, (type(None), float))
        assert hasattr(completion_handler, '__call__')

        def wrappedCompletionHandler(err, connection_handle):
            if connection_handle is None:
                completion_handler(err, None)
            else:
                completion_handler(err, _connections.Connection(connection_handle))

        _api.asyncTcpConnect(self.handle, host.encode(), port, handshake_timeout, wrappedCompletionHandler)

    def cancelConnect(self):
        _api.cancelTcpConnect(self.handle)


class SimpleTcpServer(object):
    def __init__(self, endpoint, address='127.0.0.1', port=10000, identification=None, timeout=None, log=_print):
        self._endpoint = endpoint
        self._timeout = None
        self._log = log or _dummy
        self._on_connected = None
        self._on_disconnected = None
        self._active_connections = []
        self._cv = _threading.Condition()
        self._server = TcpServer(endpoint.scheduler, address, port, identification)
        self._log('SimpleTcpServer listening on {}:{}'.format(address, port))
        self._startAccept()

    def __del__(self):
        try:
            self._server.cancelAccept()
        except:
            pass

        for connection in self._active_connections:
            connection.tryDestroy()

    def _startAccept(self):
        try:
            self._log('Waiting for incoming connection...')
            self._server.asyncAccept(self.timeout, self._onAccepted)
        except Exception as e:
            self._log('Waiting for incoming connection failed: {}'.format(e))

    def _onAccepted(self, err, connection):
        if err.error_code == _ErrorCodes.CANCELED:
            return

        self._log('Connection {} accepted'.format(connection.description))

        if isinstance(self.endpoint, _leaf.Leaf) and len(self._active_connections):
            self._log('Destroying previous connection...')
            with self._cv:
                self._active_connections[0].tryDestroy()
                self._active_connections = []

        self._log('Assigning connection to the endpoint...')
        try:
            connection.assign(self.endpoint, self.timeout)
            connection.asyncAwaitDeath(lambda err: self._onConnectionDied(err, connection))

            if self._on_connected:
                self._on_connected(connection)

            with self._cv:
                self._active_connections.append(connection)
                self._cv.notifyAll()

        except Exception as e:
            self._log('Failed to assign connection to the endpoint: {}', e)
            connection.tryDestroy()

        self._startAccept()

    def _onConnectionDied(self, err, connection):
        self._log('Connection {} died: {}'.format(connection.description, err))

        if self._on_disconnected:
            self._on_disconnected(err, connection)

        with self._cv:
            self._active_connections.remove(connection)
            self._cv.notifyAll()

        self._destroyConnectionLater(connection)

    @staticmethod
    def _destroyConnectionLater(connection):
        def killer():
            connection.tryDestroy()
        thread = _threading.Thread(target=killer)
        thread.setDaemon(True)
        thread.start()

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def address(self):
        return self._server.address

    @property
    def port(self):
        return self._server.port

    @property
    def identification(self):
        return self._server.identification

    @property
    def timeout(self):
        return self._timeout

    @property
    def on_connected(self):
        return self._on_connected

    @on_connected.setter
    def on_connected(self, fn):
        self._on_connected = fn

    @property
    def on_disconnected(self):
        return self._on_disconnected

    @on_disconnected.setter
    def on_disconnected(self, fn):
        self._on_disconnected = fn

    def waitUntilAtLeastOneConnected(self):
        with self._cv:
            while len(self._active_connections) == 0:
                self._cv.wait()

    def waitUntilAllDisconnected(self):
        with self._cv:
            while len(self._active_connections) > 0:
                self._cv.wait()


class SimpleTcpClient(object):
    def __init__(self, endpoint, host='127.0.0.1', port=10000, identification=None, timeout=None, log=_print):
        self._endpoint = endpoint
        self._host = host
        self._port = port
        self._timeout = None
        self._log = log or _dummy
        self._active_connection = None
        self._cv = _threading.Condition()
        self._on_connected = None
        self._on_disconnected = None
        self._client = TcpClient(endpoint.scheduler, identification)
        self._startConnect()

    def __del__(self):
        try:
            self._client.cancelConnect()
        except:
            pass

        if self._active_connection:
            self._active_connection.tryDestroy()

    def _startConnect(self):
        try:
            self._log('Connecting to {}:{}...'.format(self.host, self.port))
            self._client.asyncConnect(self._host, self._port, self.timeout, self._onConnected)
        except Exception as e:
            self._log('Connecting to {}:{} failed: {}'.format(self.host, self.port, e))

    def _startConnectDelayed(self):
        _time.sleep(1.0)
        self._startConnect()

    def _onConnected(self, err, connection):
        if err.error_code == _ErrorCodes.CANCELED:
            return

        if err:
            self._log('Failed to connect to {}:{}: {}'.format(self.host, self.port, err))
            self._startConnectDelayed()
            return

        self._log('Connection {} established'.format(connection.description))
        self._log('Assigning connection to the endpoint...')
        try:
            connection.assign(self.endpoint, self.timeout)
            connection.asyncAwaitDeath(lambda err: self._onConnectionDied(err, connection))

            if self._on_connected:
                self._on_connected(connection)

            with self._cv:
                self._active_connection = connection
                self._cv.notifyAll()

        except Exception as e:
            self._log('Failed to assign connection to the endpoint: {}', e)
            connection.tryDestroy()
            self._startConnectDelayed()

    def _onConnectionDied(self, err, connection):
        self._log('Connection {} died: {}'.format(connection.description, err))

        if self._on_disconnected:
            self._on_disconnected(err, connection)

        with self._cv:
            self._active_connection = None
            self._cv.notifyAll()

        self._destroyConnectionLater(connection)

        if err.error_code != _ErrorCodes.CANCELED:
            self._startConnectDelayed()

    @staticmethod
    def _destroyConnectionLater(connection):
        def killer():
            connection.tryDestroy()
        thread = _threading.Thread(target=killer)
        thread.setDaemon(True)
        thread.start()

    @property
    def endpoint(self):
        return self._endpoint

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def identification(self):
        return self._client.identification

    @property
    def timeout(self):
        return self._timeout

    @property
    def on_connected(self):
        return self._on_connected

    @on_connected.setter
    def on_connected(self, fn):
        self._on_connected = fn

    @property
    def on_disconnected(self):
        return self._on_disconnected

    @on_disconnected.setter
    def on_disconnected(self, fn):
        self._on_disconnected = fn

    def waitUntilConnected(self):
        with self._cv:
            while self._active_connection is None:
                self._cv.wait()

    def waitUntilDisconnected(self):
        with self._cv:
            while self._active_connection is not None:
                self._cv.wait()
