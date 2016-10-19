import ctypes as _ctypes
import platform as _platform
import enum as _enum
import atexit as _atexit
import typing as _typing


# ======================================================================================================================
# Load the shared library
# ======================================================================================================================
_library_filename = None
if _platform.system() == 'Windows':
    _library_filename = "chirp.dll"
elif _platform.system() == 'Linux':
    _library_filename = "libchirp.so"
else:
    raise Exception(_platform.system() + ' is not supported')

try:
    _chirp = _ctypes.cdll.LoadLibrary(_library_filename)
except Exception as e:
    raise Exception('ERROR: Could not load {}: {}. Make sure the library is in your library search path.'
                    .format(_library_filename, e))


# ======================================================================================================================
# Result and error codes
# ======================================================================================================================
_chirp.CHIRP_GetErrorString.restype = _ctypes.c_char_p
_chirp.CHIRP_GetErrorString.argtypes = [_ctypes.c_int]


class Result:
    def __init__(self, value: int):
        self._value = value

    @property
    def value(self):
        return self._value

    def __bool__(self):
        return self._value >= 0

    def __eq__(self, other):
        return self._value == other.value and isinstance(other, Result)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        s = _chirp.CHIRP_GetErrorString(self._value if self._value < 0 else 0).decode()
        return '[{}] {}'.format(self._value, s)


class Error(Exception, Result):
    def __init__(self, value: int):
        assert value < 0
        Result.__init__(self, value)


class Success(Result):
    def __init__(self, value: int = 0):
        assert value >= 0
        Result.__init__(self, value)


def _api_result_handler(result: int) -> Success:
    if result < 0:
        raise Error(result)
    else:
        return Success(result)


# ======================================================================================================================
# Initialise the library and clean up on exit
# ======================================================================================================================
_chirp.CHIRP_Initialise.restype = Result
_chirp.CHIRP_Initialise.argtypes = []

_res = _chirp.CHIRP_Initialise()
if not _res:
    raise Exception('ERROR: Could not initialise CHIRP: {}'.format(_res))


_chirp.CHIRP_Shutdown.restype = Result
_chirp.CHIRP_Shutdown.argtypes = []
_atexit.register(_chirp.CHIRP_Shutdown)


# ======================================================================================================================
# Helpers
# ======================================================================================================================
class ControlFlow(_enum.Enum):
    CONTINUE = 0
    STOP = 1


_callback_function_to_keep_alive = set()


class _StoredCallbackFunction(object):
    def __init__(self, wrapped_fn):
        self.__wrapped_fn = wrapped_fn


def _wrap_callback(c_function_type, fn):
    stored_object = None
    def clb(res, *args):
        if res < 0:
            ret = fn(Error(res), *args[:-1])
        else:
            ret = fn(Success(res), *args[:-1])
        if ret is None or ret == ControlFlow.STOP:
            _callback_function_to_keep_alive.remove(stored_object)
        return ret
    wrapped_fn = c_function_type(clb)
    stored_object = _StoredCallbackFunction(wrapped_fn)
    _callback_function_to_keep_alive.add(stored_object)

    return wrapped_fn


def _make_api_timeout(timeout):
    if timeout is None:
        return -1
    else:
        return int(timeout * 1000)


# ======================================================================================================================
# Free functions
# ======================================================================================================================
class Verbosity(_enum.Enum):
    TRACE = 5
    DEBUG = 4
    INFO = 3
    WARNING = 2
    ERROR = 1
    FATAL = 0


_chirp.CHIRP_GetVersion.restype = _ctypes.c_char_p
_chirp.CHIRP_GetVersion.argtypes = []


def get_version() -> str:
    return _chirp.CHIRP_GetVersion().decode()


_chirp.CHIRP_SetLogFile.restype = _api_result_handler
_chirp.CHIRP_SetLogFile.argtypes = [_ctypes.c_char_p, _ctypes.c_int]


def set_log_file(filename: str, verbosity: Verbosity) -> None:
    _chirp.CHIRP_SetLogFile(filename.encode('utf-8'), verbosity.value)


# ======================================================================================================================
# Object
# ======================================================================================================================
_chirp.CHIRP_Destroy.restype = _api_result_handler
_chirp.CHIRP_Destroy.argtypes = [_ctypes.c_void_p]


class Object:
    def __init__(self, handle: _ctypes.c_void_p):
        self._handle = handle

    def destroy(self) -> None:
        _chirp.CHIRP_Destroy(self._handle)
        self._handle = None

    def __del__(self):
        if self._handle is not None:
            try:
                _chirp.CHIRP_Destroy(self._handle)
            except Error:
                pass

    def __str__(self):
        handle_str = '{:#010x}'.format(self._handle.value) if self._handle.value else 'INVALID'
        return '{} [{}]'.format(self.__class__.__name__, handle_str)


# ======================================================================================================================
# Scheduler
# ======================================================================================================================
_chirp.CHIRP_CreateScheduler.restype = _api_result_handler
_chirp.CHIRP_CreateScheduler.argtypes = [_ctypes.POINTER(_ctypes.c_void_p)]

_chirp.CHIRP_SetSchedulerThreadPoolSize.restype = _api_result_handler
_chirp.CHIRP_SetSchedulerThreadPoolSize.argtypes = [_ctypes.c_void_p, _ctypes.c_uint]


class Scheduler(Object):
    def __init__(self):
        handle = _ctypes.c_void_p()
        _chirp.CHIRP_CreateScheduler(_ctypes.byref(handle))
        Object.__init__(self, handle)

    def set_thread_pool_size(self, n: int) -> None:
        _chirp.CHIRP_SetSchedulerThreadPoolSize(self._handle, n)


# ======================================================================================================================
# Signature
# ======================================================================================================================
class Signature:
    def __init__(self, raw: int = 0):
        self._raw = raw

    @property
    def raw(self) -> int:
        return self._raw

    def __eq__(self, other):
        if isinstance(other, int):
            return self._raw == other
        else:
            return self._raw == other.raw and isinstance(other, Signature)

    def __ne__(self, other):
        return not (self == other)

    def __str__(self):
        return '{:#010x}'.format(self._raw)[2:]


# ======================================================================================================================
# Endpoint, Leaf and Node
# ======================================================================================================================
class Endpoint(Object):
    def __init__(self, handle: _ctypes.c_void_p, scheduler: Scheduler):
        Object.__init__(self, handle)
        self._scheduler = scheduler

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler


_chirp.CHIRP_CreateLeaf.restype = _api_result_handler
_chirp.CHIRP_CreateLeaf.argtypes = [_ctypes.c_void_p]


class Leaf(Endpoint):
    def __init__(self, scheduler: Scheduler):
        handle = _ctypes.c_void_p()
        _chirp.CHIRP_CreateLeaf(_ctypes.byref(handle), scheduler._handle)
        Endpoint.__init__(self, handle, scheduler)


_chirp.CHIRP_CreateNode.restype = _api_result_handler
_chirp.CHIRP_CreateNode.argtypes = [_ctypes.c_void_p]


class Node(Endpoint):
    def __init__(self, scheduler: Scheduler):
        handle = _ctypes.c_void_p()
        _chirp.CHIRP_CreateNode(_ctypes.byref(handle), scheduler._handle)
        Endpoint.__init__(self, handle, scheduler)

    def get_known_terminals(self):
        # TODO: Implement
        raise NotImplementedError()

    def async_await_known_terminals_change(self):
        # TODO: Implement
        raise NotImplementedError()

    def cancel_await_known_terminals_change(self):
        # TODO: Implement
        raise NotImplementedError()


# ======================================================================================================================
# Connections
# ======================================================================================================================
_chirp.CHIRP_GetConnectionDescription.restype = _api_result_handler
_chirp.CHIRP_GetConnectionDescription.argtypes = [_ctypes.c_void_p, _ctypes.c_char_p, _ctypes.c_uint]

_chirp.CHIRP_GetRemoteVersion.restype = _api_result_handler
_chirp.CHIRP_GetRemoteVersion.argtypes = [_ctypes.c_void_p, _ctypes.c_char_p, _ctypes.c_uint]

_chirp.CHIRP_GetRemoteIdentification.restype = _api_result_handler
_chirp.CHIRP_GetRemoteIdentification.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p, _ctypes.c_uint,
                                                 _ctypes.POINTER(_ctypes.c_uint)]

_chirp.CHIRP_AssignConnection.restype = _api_result_handler
_chirp.CHIRP_AssignConnection.argtypes = [_ctypes.c_void_p, _ctypes.c_void_p, _ctypes.c_int]

_chirp.CHIRP_AsyncAwaitConnectionDeath.restype = _api_result_handler
_chirp.CHIRP_AsyncAwaitConnectionDeath.argtypes = [_ctypes.c_void_p,
                                                   _ctypes.CFUNCTYPE(None, _ctypes.c_int, _ctypes.c_void_p),
                                                   _ctypes.c_void_p]

_chirp.CHIRP_CancelAwaitConnectionDeath.restype = _api_result_handler
_chirp.CHIRP_CancelAwaitConnectionDeath.argtypes = [_ctypes.c_void_p]

_chirp.CHIRP_CreateLocalConnection.restype = _api_result_handler
_chirp.CHIRP_CreateLocalConnection.argtypes = [_ctypes.POINTER(_ctypes.c_void_p), _ctypes.c_void_p, _ctypes.c_void_p]


class Connection(Object):
    STRING_BUFFER_SIZE = 128

    def __init__(self, handle: _ctypes.c_void_p):
        Object.__init__(self, handle)

    @property
    def description(self) -> str:
        buffer = _ctypes.create_string_buffer(self.STRING_BUFFER_SIZE)
        _chirp.CHIRP_GetConnectionDescription(self._handle, buffer, _ctypes.sizeof(buffer))
        return _ctypes.string_at(_ctypes.addressof(buffer)).decode()

    @property
    def remote_version(self) -> str:
        buffer = _ctypes.create_string_buffer(self.STRING_BUFFER_SIZE)
        _chirp.CHIRP_GetRemoteVersion(self._handle, buffer, _ctypes.sizeof(buffer))
        return _ctypes.string_at(_ctypes.addressof(buffer)).decode()

    @property
    def remote_identification(self) -> _typing.Union[str, None]:
        buffer = _ctypes.create_string_buffer(self.STRING_BUFFER_SIZE)
        bytes_written = _ctypes.c_uint()
        _chirp.CHIRP_GetRemoteIdentification(self._handle, buffer, _ctypes.sizeof(buffer), _ctypes.byref(bytes_written))
        if bytes_written.value == 0:
            return None
        else:
            return _ctypes.string_at(_ctypes.addressof(buffer)).decode()


class LocalConnection(Connection):
    def __init__(self, endpointA: Endpoint, endpointB: Endpoint):
        handle = _ctypes.c_void_p()
        _chirp.CHIRP_CreateLocalConnection(_ctypes.byref(handle), endpointA._handle, endpointB._handle)
        Connection.__init__(self, handle)


class NonLocalConnection(Connection):
    def __init__(self, handle: _ctypes.c_void_p):
        Connection.__init__(self, handle)

    def assign(self, endpoint: Endpoint, timeout: _typing.Union[float, None] = None) -> None:
        _chirp.CHIRP_AssignConnection(self._handle, endpoint._handle, _make_api_timeout(timeout))

    def async_await_death(self, completion_handler: _typing.Callable[[Error], None]) -> None:
        _chirp.CHIRP_AsyncAwaitConnectionDeath(self._handle, _wrap_callback(
            _chirp.CHIRP_AsyncAwaitConnectionDeath.argtypes[1], completion_handler), _ctypes.c_void_p())

    def cancel_await_death(self) -> None:
        _chirp.CHIRP_CancelAwaitConnectionDeath(self._handle)


# ======================================================================================================================
# TCP connections
# ======================================================================================================================
class TcpConnection(NonLocalConnection):
    def __init__(self, handle: _ctypes.c_void_p):
        NonLocalConnection.__init__(self, handle)


_chirp.CHIRP_CreateTcpClient.restype = _api_result_handler
_chirp.CHIRP_CreateTcpClient.argtypes = [_ctypes.POINTER(_ctypes.c_void_p), _ctypes.c_void_p, _ctypes.c_void_p,
                                         _ctypes.c_uint]

_chirp.CHIRP_AsyncTcpConnect.restype = _api_result_handler
_chirp.CHIRP_AsyncTcpConnect.argtypes = [_ctypes.c_void_p, _ctypes.c_char_p, _ctypes.c_uint, _ctypes.c_int,
                                         _ctypes.CFUNCTYPE(None, _ctypes.c_int, _ctypes.c_void_p, _ctypes.c_void_p),
                                         _ctypes.c_void_p]

_chirp.CHIRP_CancelTcpConnect.restype = _api_result_handler
_chirp.CHIRP_CancelTcpConnect.argtypes = [_ctypes.c_void_p]


class TcpClient(Object):
    def __init__(self, scheduler: Scheduler, identification: _typing.Union[str, None] = None):
        handle = _ctypes.c_void_p()
        if identification is None:
            _chirp.CHIRP_CreateTcpClient(_ctypes.byref(handle), scheduler._handle, _ctypes.c_void_p(), 0)
        else:
            buffer = _ctypes.create_string_buffer(identification.encode('utf-8'))
            _chirp.CHIRP_CreateTcpClient(_ctypes.byref(handle), scheduler._handle, buffer, _ctypes.sizeof(buffer))
        Object.__init__(self, handle)
        self._scheduler = scheduler
        self._identification = identification

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def identification(self) -> _typing.Union[str, None]:
        return self._identification

    def async_connect(self, host: str, port: int, handshake_timeout: float,
                      completion_handler: _typing.Callable[[Result, _typing.Union[TcpConnection, None]], None]) -> None:
        def fn(res, connection_handle):
            connection = None
            if res:
                connection = TcpConnection(_ctypes.cast(connection_handle, _ctypes.c_void_p))
            completion_handler(res, connection)

        _chirp.CHIRP_AsyncTcpConnect(self._handle, host.encode('utf-8'), port, _make_api_timeout(handshake_timeout),
                                     _wrap_callback(_chirp.CHIRP_AsyncTcpConnect.argtypes[4], fn), _ctypes.c_void_p())

    def cancel_connect(self) -> None:
        _chirp.CHIRP_CancelTcpConnect(self._handle)


_chirp.CHIRP_CreateTcpServer.restype = _api_result_handler
_chirp.CHIRP_CreateTcpServer.argtypes = [_ctypes.POINTER(_ctypes.c_void_p), _ctypes.c_void_p, _ctypes.c_char_p,
                                         _ctypes.c_uint, _ctypes.c_void_p, _ctypes.c_uint]

_chirp.CHIRP_AsyncTcpAccept.restype = _api_result_handler
_chirp.CHIRP_AsyncTcpAccept.argtypes = [_ctypes.c_void_p, _ctypes.c_int,
                                        _ctypes.CFUNCTYPE(None, _ctypes.c_int, _ctypes.c_void_p, _ctypes.c_void_p),
                                        _ctypes.c_void_p]

_chirp.CHIRP_CancelTcpAccept.restype = _api_result_handler
_chirp.CHIRP_CancelTcpAccept.argtypes = [_ctypes.c_void_p]


class TcpServer(Object):
    def __init__(self, scheduler: Scheduler, address: str, port: int, identification: _typing.Union[str, None] = None):
        handle = _ctypes.c_void_p()
        if identification is None:
            _chirp.CHIRP_CreateTcpServer(_ctypes.byref(handle), scheduler._handle, address.encode('utf-8'), port,
                                         _ctypes.c_void_p(), 0)
        else:
            buffer = _ctypes.create_string_buffer(identification.encode('utf-8'))
            _chirp.CHIRP_CreateTcpServer(_ctypes.byref(handle), scheduler._handle, address.encode('utf-8'), port,
                                         buffer, _ctypes.sizeof(buffer))
        Object.__init__(self, handle)
        self._scheduler = scheduler
        self._address = address
        self._port = port
        self._identification = identification


    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def address(self) -> str:
        return self._address

    @property
    def port(self) -> int:
        return self._port

    @property
    def identification(self) -> _typing.Union[str, None]:
        return self._identification

    def async_accept(self, handshake_timeout: float,
                      completion_handler: _typing.Callable[[Result, _typing.Union[TcpConnection, None]], None]) -> None:
        def fn(res, connection_handle):
            connection = None
            if res:
                connection = TcpConnection(_ctypes.cast(connection_handle, _ctypes.c_void_p))
            completion_handler(res, connection)

        _chirp.CHIRP_AsyncTcpAccept(self._handle, _make_api_timeout(handshake_timeout),
                                     _wrap_callback(_chirp.CHIRP_AsyncTcpAccept.argtypes[2], fn), _ctypes.c_void_p())

    def cancel_accept(self) -> None:
        _chirp.CHIRP_CancelTcpAccept(self._handle)