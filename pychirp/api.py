from ctypes import *
from struct import *
import platform

GET_KNOWN_TERMINALS_BUFFER_SIZE          = 1024**2
AWAIT_KNOWN_TERMINALS_CHANGE_BUFFER_SIZE = 256
GET_CONNECTION_DESCRIPTION_BUFFER_SIZE   = 64
GET_REMOTE_VERSION_BUFFER_SIZE           = 32
GET_REMOTE_IDENTIFICATION_BUFFER_SIZE    = 1024
RECEIVE_MESSAGE_BUFFER_SIZE              = 1024 * 64

ASYNC_AWAIT_KNOWN_TERMINALS_CHANGE_CALLBACK    = CFUNCTYPE(None, c_int, c_void_p)
ASYNC_GET_BINDING_STATE_CALLBACK               = CFUNCTYPE(None, c_int, c_int, c_void_p)
ASYNC_AWAIT_BINDING_STATE_CHANGE_CALLBACK      = CFUNCTYPE(None, c_int, c_int, c_void_p)
ASYNC_GET_SUBSCRIPTION_STATE_CALLBACK          = CFUNCTYPE(None, c_int, c_int, c_void_p)
ASYNC_AWAIT_SUBSCRIPTION_STATE_CHANGE_CALLBACK = CFUNCTYPE(None, c_int, c_int, c_void_p)
ASYNC_TCP_ACCEPT_CALLBACK                      = CFUNCTYPE(None, c_int, c_void_p, c_void_p)
ASYNC_TCP_CONNECT_CALLBACK                     = CFUNCTYPE(None, c_int, c_void_p, c_void_p)
ASYNC_AWAIT_CONNECTION_DEATH_CALLBACK          = CFUNCTYPE(None, c_int, c_void_p)
PS_ASYNC_RECEIVE_MESSAGE_CALLBACK              = CFUNCTYPE(None, c_int, c_uint, c_void_p)
SG_ASYNC_SCATTER_GATHER_CALLBACK               = CFUNCTYPE(c_int, c_int, c_int, c_int, c_uint, c_void_p)
SG_ASYNC_RECEIVE_SCATTERED_MESSAGE_CALLBACK    = CFUNCTYPE(None, c_int, c_int, c_uint, c_void_p)
CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK             = CFUNCTYPE(None, c_int, c_uint, c_int, c_void_p)


class ErrorCodes:
    OK = 0
    UNKNOWN = -1
    INVALID_HANDLE = -2
    WRONG_OBJECT_TYPE = -3
    OBJECT_STILL_USED = -4
    BAD_ALLOCATION = -5
    INVALID_PARAM = -6
    ALREADY_CONNECTED = -7
    AMBIGUOUS_IDENTIFIER = -8
    ALREADY_INITIALISED = -9
    NOT_INITIALISED = -10
    CANNOT_CREATE_LOG_FILE = -11
    CANCELED = -12
    ASYNC_OPERATION_RUNNING = -13
    BUFFER_TOO_SMALL = -14
    NOT_BOUND = -15
    INVALID_ID = -16
    IDENTIFICATION_TOO_LARGE = -17
    INVALID_IP_ADDRESS = -18
    INVALID_PORT_NUMBER = -19
    CANNOT_OPEN_SOCKET = -20
    CANNOT_BIND_SOCKET = -21
    CANNOT_LISTEN_ON_SOCKET = -22
    SOCKET_BROKEN = -23
    INVALID_MAGIC_PREFIX = -24
    INCOMPATIBLE_VERSION = -25
    ACCEPT_FAILED = -26
    TIMEOUT = -27
    ADDRESS_IN_USE = -28
    RESOLVE_FAILED = -29
    CONNECTION_REFUSED = -30
    HOST_UNREACHABLE = -31
    NETWORK_DOWN = -32
    CONNECT_FAILED = -33
    NOT_READY = -34
    ALREADY_ASSIGNED = -35
    CONNECTION_DEAD = -36
    CONNECTION_CLOSED = -37
    UNINITIALIZED = -38


class Verbosity:
    TRACE   = 0
    DEBUG   = 1
    INFO    = 2
    WARNING = 3
    ERROR   = 4
    FATAL   = 5


class TerminalTypes:
    DEAF_MUTE                = 0
    PUBLISH_SUBSCRIBE        = 1
    SCATTER_GATHER           = 2
    CACHED_PUBLISH_SUBSCRIBE = 3
    PRODUCER                 = 4
    CONSUMER                 = 5
    CACHED_PRODUCER          = 6
    CACHED_CONSUMER          = 7
    MASTER                   = 8
    SLAVE                    = 9
    CACHED_MASTER            = 10
    CACHED_SLAVE             = 11
    SERVICE                  = 12
    CLIENT                   = 13


class ControlFlow:
    CONTINUE = 0
    STOP     = 1


class ScatterGatherFlags:
    NO_FLAGS          = 0
    FINISHED          = 1 << 0
    IGNORED           = 1 << 1
    DEAF              = 1 << 2
    BINDING_DESTROYED = 1 << 3
    CONNECTION_LOST   = 1 << 4


class Result(object):
    def __init__(self, returned_value):
        self.__returned_value = returned_value

    @property
    def returned_value(self):
        return self.__returned_value

    def __str__(self):
        if self.returned_value > 0:
            return 'ID:'.format(self.returned_value)
        else:
            return str(ErrorCode(self))

    def __bool__(self):
        return self.returned_value >= 0
    __nonzero__ = __bool__


class ErrorCode(Exception):
    def __init__(self, result):
        assert result.returned_value <= 0
        self.__error_code = result.returned_value

    def __str__(self):
        return getErrorString(self.error_code)

    @property
    def error_code(self):
        return self.__error_code

    def __bool__(self):
        return self.error_code < 0
    __nonzero__ = __bool__


class Handle(object):
    def __init__(self, handle=None):
        if handle is None:
            self.__handle = c_void_p()
        else:
            assert isinstance(handle, c_void_p)
            self.__handle = handle

    @property
    def _as_parameter_(self):
        return self.__handle

    def __str__(self):
        return 'Handle:{}'.format(str(self.__handle.value))

    def __bool__(self):
        return bool(self.__handle)
    __nonzero__ = __bool__


class OperationId(object):
    def __init__(self, id):
        assert isinstance(id, int)
        self.__id = id

    @property
    def _as_parameter_(self):
        return self.__id

    def __str__(self):
        return 'Operation:{}'.format(self.__id)

    def __bool__(self):
        return bool(self.__id)
    __nonzero__ = __bool__

    def __eq__(self, rhs):
        if isinstance(rhs, OperationId):
            return self.__id == rhs.__id
        return NotImplemented

    def __ne__(self, rhs):
        result = self.__eq__(rhs)
        if result is NotImplemented:
            return result
        return not result


def _return_string(shared_lib_fn, argtypes):
    shared_lib_fn.restype = c_char_p
    shared_lib_fn.argtypes = argtypes
    def decorator(fn):
        def wrapper(*args):
            return shared_lib_fn(*args).decode()
        return wrapper
    return decorator


def _return_result(shared_lib_fn, argtypes):
    shared_lib_fn.restype = Result
    shared_lib_fn.argtypes = argtypes
    def decorator(fn):
        def wrapper(*args):
            res = shared_lib_fn(*args)
            if not res:
                raise ErrorCode(res)
            return res
        return wrapper
    return decorator


def _return_void(shared_lib_fn, argtypes):
    shared_lib_fn.restype = Result
    shared_lib_fn.argtypes = argtypes
    def decorator(fn):
        def wrapper(*args):
            res = shared_lib_fn(*args)
            if not res:
                raise ErrorCode(res)
        return wrapper
    return decorator


def _return_first_parameter_as_handle(shared_lib_fn, argtypes):
    shared_lib_fn.restype = Result
    shared_lib_fn.argtypes = argtypes
    def decorator(fn):
        def wrapper(*args):
            handle = Handle()
            res = shared_lib_fn(byref(handle._as_parameter_), *args)
            if not res:
                raise ErrorCode(res)
            return handle
        return wrapper
    return decorator


def _custom_call(shared_lib_fn, argtypes):
    shared_lib_fn.restype = Result
    shared_lib_fn.argtypes = argtypes
    def decorator(fn):
        def wrapper(*args):
            return fn(*args)
        return wrapper
    return decorator


if platform.system() == 'Windows':
    _chirp = cdll.LoadLibrary("chirp.dll")
elif platform.system() == 'Linux':
    _chirp = cdll.LoadLibrary("libchirp.so")
else:
    raise Exception(platform.system() + ' is not supported yet')


class _CallbackFunction(object):
    def __init__(self, wrapped_fn):
        self.__wrapped_fn = wrapped_fn

_callback_functions = set() # for tricking the garbage collector
def _wrap_callback(wrapper_type, fn):
    stored_object = None
    def clb(*args):
        ret = fn(*args)
        if ret is None or ret == ControlFlow.STOP:
            _callback_functions.remove(stored_object)
        return ret
    wrapped_fn = wrapper_type(clb)
    stored_object = _CallbackFunction(wrapped_fn)
    _callback_functions.add(stored_object)

    return wrapped_fn


@_return_string(_chirp.CHIRP_GetVersion, [])
def getVersion():
    pass


@_return_string(_chirp.CHIRP_GetErrorString, [c_int])
def getErrorString(error_code):
    pass


@_return_void(_chirp.CHIRP_SetLogFile, [c_char_p, c_int])
def setLogFile(file, verbosity):
    pass


@_return_void(_chirp.CHIRP_Initialise, [])
def initialise():
    pass


@_return_void(_chirp.CHIRP_Shutdown, [])
def shutdown():
    pass


@_return_void(_chirp.CHIRP_Destroy, [c_void_p])
def destroy(object_handle):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateScheduler, [POINTER(c_void_p)])
def createScheduler():
    pass


@_return_void(_chirp.CHIRP_SetSchedulerThreadPoolSize, [c_void_p, c_uint])
def setSchedulerThreadPoolSize(scheduler_handle, num_threads):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateNode, [POINTER(c_void_p), c_void_p])
def createNode(scheduler_handle):
    pass


@_custom_call(_chirp.CHIRP_GetKnownTerminals, [c_void_p, c_void_p, c_uint, POINTER(c_uint)])
def getKnownTerminals(node_handle):
    buf = create_string_buffer(GET_KNOWN_TERMINALS_BUFFER_SIZE)
    num_terminals = c_uint()
    res = _chirp.CHIRP_GetKnownTerminals(node_handle, buf, sizeof(buf), byref(num_terminals))
    if not res:
        raise ErrorCode(res)

    terminals = []
    offset = 0
    for _ in range(num_terminals.value):
        info_struct = Struct('=cI')
        (terminal_type, signature) = info_struct.unpack_from(buf, offset)
        offset += info_struct.size

        name = string_at(addressof(buf) + offset)
        offset += len(name) + 1

        terminals.append({
            'type'      : ord(terminal_type),
            'signature' : signature,
            'name'      : name.decode()
        })

    return terminals


@_custom_call(_chirp.CHIRP_AsyncAwaitKnownTerminalsChange, [c_void_p, c_void_p, c_uint, ASYNC_AWAIT_KNOWN_TERMINALS_CHANGE_CALLBACK, c_void_p])
def asyncAwaitKnownTerminalsChange(node_handle, completion_handler):
    buf = create_string_buffer(AWAIT_KNOWN_TERMINALS_CHANGE_BUFFER_SIZE)
    def fn(res, user_arg):

        err = ErrorCode(Result(res))
        info = None
        if not err:
            info_struct = Struct('=ccI')
            (added, terminal_type, signature) = info_struct.unpack_from(buf)
            name = string_at(addressof(buf) + info_struct.size)
            info = {
                'added'     : ord(added) == 1,
                'type'      : ord(terminal_type),
                'signature' : signature,
                'name'      : name.decode()
            }
        completion_handler(err, info)

    res = _chirp.CHIRP_AsyncAwaitKnownTerminalsChange(node_handle, buf, sizeof(buf), _wrap_callback(ASYNC_AWAIT_KNOWN_TERMINALS_CHANGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelAwaitKnownTerminalsChange, [c_void_p])
def cancelAwaitKnownTerminalsChange(node_handle):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateLeaf, [POINTER(c_void_p), c_void_p])
def createLeaf(scheduler_handle):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateTerminal, [POINTER(c_void_p), c_void_p, c_int, c_char_p, c_uint])
def createTerminal(leaf_handle, terminal_type, name, signature):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateBinding, [POINTER(c_void_p), c_void_p, c_char_p])
def createBinding(terminal_handle, targets):
    pass


@_custom_call(_chirp.CHIRP_GetBindingState, [c_void_p, POINTER(c_int)])
def getBindingState(binding_handle):
    state = c_int()
    res = _chirp.CHIRP_GetBindingState(binding_handle, byref(state))
    if not res:
        raise ErrorCode(res)

    return False if state.value == 0 else True


@_custom_call(_chirp.CHIRP_AsyncGetBindingState, [c_void_p, ASYNC_GET_BINDING_STATE_CALLBACK, c_void_p])
def asyncGetBindingState(binding_handle, completion_handler):
    def fn(res, state, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = False if state == 0 else True

        completion_handler(err, info)

    res = _chirp.CHIRP_AsyncGetBindingState(binding_handle, _wrap_callback(ASYNC_GET_BINDING_STATE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_AsyncAwaitBindingStateChange, [c_void_p, ASYNC_AWAIT_BINDING_STATE_CHANGE_CALLBACK, c_void_p])
def asyncAwaitBindingStateChange(binding_handle, completion_handler):
    def fn(res, state, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = False if state == 0 else True

        completion_handler(err, info)

    res = _chirp.CHIRP_AsyncAwaitBindingStateChange(binding_handle, _wrap_callback(ASYNC_AWAIT_BINDING_STATE_CHANGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelAwaitBindingStateChange, [c_void_p])
def cancelAwaitBindingStateChange(binding_handle):
    pass


@_custom_call(_chirp.CHIRP_GetSubscriptionState, [c_void_p, POINTER(c_int)])
def getSubscriptionState(terminal_handle):
    state = c_int()
    res = _chirp.CHIRP_GetSubscriptionState(terminal_handle, byref(state))
    if not res:
        raise ErrorCode(res)

    return False if state.value == 0 else True


@_custom_call(_chirp.CHIRP_AsyncGetSubscriptionState, [c_void_p, ASYNC_GET_SUBSCRIPTION_STATE_CALLBACK, c_void_p])
def asyncGetSubscriptionState(terminal_handle, completion_handler):
    def fn(res, state, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = False if state == 0 else True

        completion_handler(err, info)

    res = _chirp.CHIRP_AsyncGetSubscriptionState(terminal_handle, _wrap_callback(ASYNC_GET_SUBSCRIPTION_STATE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_AsyncAwaitSubscriptionStateChange, [c_void_p, ASYNC_AWAIT_SUBSCRIPTION_STATE_CHANGE_CALLBACK, c_void_p])
def asyncAwaitSubscriptionStateChange(terminal_handle, completion_handler):
    def fn(res, state, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = False if state == 0 else True

        completion_handler(err, info)

    res = _chirp.CHIRP_AsyncAwaitSubscriptionStateChange(terminal_handle, _wrap_callback(ASYNC_AWAIT_SUBSCRIPTION_STATE_CHANGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelAwaitSubscriptionStateChange, [c_void_p])
def cancelAwaitSubscriptionStateChange(terminal_handle):
    pass


@_return_first_parameter_as_handle(_chirp.CHIRP_CreateLocalConnection, [POINTER(c_void_p), c_void_p, c_void_p])
def createLocalConnection(leaf_or_node_a, leaf_or_node_b):
    pass


@_custom_call(_chirp.CHIRP_CreateTcpServer, [POINTER(c_void_p), c_void_p, c_char_p, c_uint, c_void_p, c_uint])
def createTcpServer(scheduler_handle, address, port, identification):
    handle = Handle()
    if identification is None:
        res = _chirp.CHIRP_CreateTcpServer(byref(handle._as_parameter_), scheduler_handle, address, port, c_void_p(), 0)
    else:
        buf = create_string_buffer(bytes(identification))
        res = _chirp.CHIRP_CreateTcpServer(byref(handle._as_parameter_), scheduler_handle, address, port, buf, sizeof(buf) - 1)

    if not res:
        raise ErrorCode(res)

    return handle


@_custom_call(_chirp.CHIRP_AsyncTcpAccept, [c_void_p, c_int, ASYNC_TCP_ACCEPT_CALLBACK, c_void_p])
def asyncTcpAccept(tcp_server_handle, handshake_timeout, completion_handler):
    def fn(res, connection_handle, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = Handle(cast(connection_handle, c_void_p))
        completion_handler(err, info)

    timeout_in_ms = -1 if handshake_timeout is None else int(handshake_timeout * 1000)
    res = _chirp.CHIRP_AsyncTcpAccept(tcp_server_handle, timeout_in_ms, _wrap_callback(ASYNC_TCP_ACCEPT_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelTcpAccept, [c_void_p])
def cancelTcpAccept(tcp_server_handle):
    pass


@_custom_call(_chirp.CHIRP_CreateTcpClient, [POINTER(c_void_p), c_void_p, c_void_p, c_uint])
def createTcpClient(scheduler_handle, identification):
    handle = Handle()
    if identification is None:
        res = _chirp.CHIRP_CreateTcpClient(byref(handle._as_parameter_), scheduler_handle, c_void_p(), 0)
    else:
        buffer = create_string_buffer(bytes(identification))
        res = _chirp.CHIRP_CreateTcpClient(byref(handle._as_parameter_), scheduler_handle, buffer, sizeof(buffer) - 1)

    if not res:
        raise ErrorCode(res)

    return handle


@_custom_call(_chirp.CHIRP_AsyncTcpConnect, [c_void_p, c_char_p, c_uint, c_int, ASYNC_TCP_CONNECT_CALLBACK, c_void_p])
def asyncTcpConnect(tcp_client_handle, host, port, handshake_timeout, completion_handler):
    def fn(res, connection_handle, user_arg):
        err = ErrorCode(Result(res))
        info = None
        if not err:
            info = Handle(cast(connection_handle, c_void_p))
        completion_handler(err, info)

    timeout_in_ms = -1 if handshake_timeout is None else int(handshake_timeout * 1000)
    res = _chirp.CHIRP_AsyncTcpConnect(tcp_client_handle, host, port, timeout_in_ms, _wrap_callback(ASYNC_TCP_CONNECT_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelTcpConnect, [c_void_p])
def cancelTcpConnect(tcp_client_handle):
    pass


@_custom_call(_chirp.CHIRP_GetConnectionDescription, [c_void_p, c_char_p, c_uint])
def getConnectionDescription(connection_handle):
    buf = create_string_buffer(GET_CONNECTION_DESCRIPTION_BUFFER_SIZE)
    res = _chirp.CHIRP_GetConnectionDescription(connection_handle, buf, sizeof(buf))
    if not res:
        raise ErrorCode(res)

    return string_at(addressof(buf)).decode()


@_custom_call(_chirp.CHIRP_GetRemoteVersion, [c_void_p, c_char_p, c_uint])
def getRemoteVersion(connection_handle):
    buf = create_string_buffer(GET_REMOTE_VERSION_BUFFER_SIZE)
    res = _chirp.CHIRP_GetRemoteVersion(connection_handle, buf, sizeof(buf))
    if not res:
        raise ErrorCode(res)

    return string_at(addressof(buf)).decode()


@_custom_call(_chirp.CHIRP_GetRemoteIdentification, [c_void_p, c_void_p, c_uint, POINTER(c_uint)])
def getRemoteIdentification(connection_handle):
    buf = create_string_buffer(GET_REMOTE_IDENTIFICATION_BUFFER_SIZE)
    bytes_written = c_uint()
    res = _chirp.CHIRP_GetRemoteIdentification(connection_handle, buf, sizeof(buf), byref(bytes_written))
    if not res:
        raise ErrorCode(res)

    return bytearray(buf[:bytes_written.value])


@_custom_call(_chirp.CHIRP_AssignConnection, [c_void_p, c_void_p, c_int])
def assignConnection(connection_handle, leaf_or_node_handle, timeout):
    timeout_in_ms = -1 if timeout is None else int(timeout * 1000)
    res = _chirp.CHIRP_AssignConnection(connection_handle, leaf_or_node_handle, timeout_in_ms)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_AsyncAwaitConnectionDeath, [c_void_p, ASYNC_AWAIT_CONNECTION_DEATH_CALLBACK, c_void_p])
def asyncAwaitConnectionDeath(connection_handle, completion_handler):
    def fn(res, user_arg):
        err = ErrorCode(Result(res))
        completion_handler(err)

    res = _chirp.CHIRP_AsyncAwaitConnectionDeath(connection_handle, _wrap_callback(ASYNC_AWAIT_CONNECTION_DEATH_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CancelAwaitConnectionDeath, [c_void_p])
def cancelAwaitConnectionDeath(connection_handle):
    pass


@_custom_call(_chirp.CHIRP_PS_Publish, [c_void_p, c_void_p, c_uint])
def psPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_PS_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_PS_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def psAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload)

    res = _chirp.CHIRP_PS_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_PS_CancelReceiveMessage, [c_void_p])
def psCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_SG_AsyncScatterGather, [c_void_p, c_void_p, c_uint, c_void_p, c_uint, SG_ASYNC_SCATTER_GATHER_CALLBACK, c_void_p])
def sgAsyncScatterGather(terminal_handle, data, completion_handler):
    scatter_buf = create_string_buffer(bytes(data))
    gather_buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, operation_id, flags, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(gather_buf[:bytes_written])
        return completion_handler(err, OperationId(operation_id), flags, payload)

    res = _chirp.CHIRP_SG_AsyncScatterGather(terminal_handle, scatter_buf, sizeof(scatter_buf) - 1, gather_buf, sizeof(gather_buf), _wrap_callback(SG_ASYNC_SCATTER_GATHER_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)

    return OperationId(res.returned_value)


@_return_void(_chirp.CHIRP_SG_CancelScatterGather, [c_void_p, c_int])
def sgCancelScatterGather(terminal_handle, operation_id):
    pass


@_custom_call(_chirp.CHIRP_SG_AsyncReceiveScatteredMessage, [c_void_p, c_void_p, c_uint, SG_ASYNC_RECEIVE_SCATTERED_MESSAGE_CALLBACK, c_void_p])
def sgAsyncReceiveScatteredMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, operation_id, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, OperationId(operation_id), payload)

    res = _chirp.CHIRP_SG_AsyncReceiveScatteredMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(SG_ASYNC_RECEIVE_SCATTERED_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_SG_CancelReceiveScatteredMessage, [c_void_p])
def sgCancelReceiveScatteredMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_SG_RespondToScatteredMessage, [c_void_p, c_int, c_void_p, c_uint])
def sgRespondToScatteredMessage(terminal_handle, operation_id, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_SG_RespondToScatteredMessage(terminal_handle, operation_id, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_SG_IgnoreScatteredMessage, [c_void_p, c_int])
def sgIgnoreScatteredMessage(terminal_handle, operation_id):
    pass


@_custom_call(_chirp.CHIRP_CPS_Publish, [c_void_p, c_void_p, c_uint])
def cpsPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_CPS_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_CPS_GetCachedMessage, [c_void_p, c_void_p, c_uint, POINTER(c_uint)])
def cpsGetCachedMessage(terminal_handle):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    bytes_written = c_uint()
    res = _chirp.CHIRP_CPS_GetCachedMessage(terminal_handle, buf, sizeof(buf), byref(bytes_written))
    if not res:
        raise ErrorCode(res)

    payload = bytearray(buf[:bytes_written.value])
    return payload


@_custom_call(_chirp.CHIRP_CPS_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def cpsAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, cached, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload, True if cached == 1 else False)

    res = _chirp.CHIRP_CPS_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CPS_CancelReceiveMessage, [c_void_p])
def cpsCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_PC_Publish, [c_void_p, c_void_p, c_uint])
def pcPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_PC_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_PC_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def pcAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload)

    res = _chirp.CHIRP_PC_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_PC_CancelReceiveMessage, [c_void_p])
def pcCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_CPC_Publish, [c_void_p, c_void_p, c_uint])
def cpcPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_CPC_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_CPC_GetCachedMessage, [c_void_p, c_void_p, c_uint, POINTER(c_uint)])
def cpcGetCachedMessage(terminal_handle):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    bytes_written = c_uint()
    res = _chirp.CHIRP_CPC_GetCachedMessage(terminal_handle, buf, sizeof(buf), byref(bytes_written))
    if not res:
        raise ErrorCode(res)

    payload = bytearray(buf[:bytes_written.value])
    return payload


@_custom_call(_chirp.CHIRP_CPC_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def cpcAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, cached, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload, True if cached == 1 else False)

    res = _chirp.CHIRP_CPC_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CPC_CancelReceiveMessage, [c_void_p])
def cpcCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_MS_Publish, [c_void_p, c_void_p, c_uint])
def msPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_MS_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_MS_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def msAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload)

    res = _chirp.CHIRP_MS_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(PS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_MS_CancelReceiveMessage, [c_void_p])
def msCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_CMS_Publish, [c_void_p, c_void_p, c_uint])
def cmsPublish(terminal_handle, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_CMS_Publish(terminal_handle, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_custom_call(_chirp.CHIRP_CMS_GetCachedMessage, [c_void_p, c_void_p, c_uint, POINTER(c_uint)])
def cmsGetCachedMessage(terminal_handle):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    bytes_written = c_uint()
    res = _chirp.CHIRP_CMS_GetCachedMessage(terminal_handle, buf, sizeof(buf), byref(bytes_written))
    if not res:
        raise ErrorCode(res)

    payload = bytearray(buf[:bytes_written.value])
    return payload


@_custom_call(_chirp.CHIRP_CMS_AsyncReceiveMessage, [c_void_p, c_void_p, c_uint, CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, c_void_p])
def cmsAsyncReceiveMessage(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, bytes_written, cached, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, payload, True if cached == 1 else False)

    res = _chirp.CHIRP_CMS_AsyncReceiveMessage(terminal_handle, buf, sizeof(buf), _wrap_callback(CPS_ASYNC_RECEIVE_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_CMS_CancelReceiveMessage, [c_void_p])
def cmsCancelReceiveMessage(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_SC_AsyncRequest, [c_void_p, c_void_p, c_uint, c_void_p, c_uint, SG_ASYNC_SCATTER_GATHER_CALLBACK, c_void_p])
def scAsyncRequest(terminal_handle, data, completion_handler):
    scatter_buf = create_string_buffer(bytes(data))
    gather_buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, operation_id, flags, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(gather_buf[:bytes_written])
        return completion_handler(err, OperationId(operation_id), flags, payload)

    res = _chirp.CHIRP_SC_AsyncRequest(terminal_handle, scatter_buf, sizeof(scatter_buf) - 1, gather_buf, sizeof(gather_buf), _wrap_callback(SG_ASYNC_SCATTER_GATHER_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)

    return OperationId(res.returned_value)


@_return_void(_chirp.CHIRP_SC_CancelRequest, [c_void_p, c_int])
def scCancelRequest(terminal_handle, operation_id):
    pass


@_custom_call(_chirp.CHIRP_SC_AsyncReceiveRequest, [c_void_p, c_void_p, c_uint, SG_ASYNC_RECEIVE_SCATTERED_MESSAGE_CALLBACK, c_void_p])
def scAsyncReceiveRequest(terminal_handle, completion_handler):
    buf = create_string_buffer(RECEIVE_MESSAGE_BUFFER_SIZE)
    def fn(res, operation_id, bytes_written, user_arg):
        err = ErrorCode(Result(res))
        payload = bytearray(buf[:bytes_written])
        completion_handler(err, OperationId(operation_id), payload)

    res = _chirp.CHIRP_SC_AsyncReceiveRequest(terminal_handle, buf, sizeof(buf), _wrap_callback(SG_ASYNC_RECEIVE_SCATTERED_MESSAGE_CALLBACK, fn), c_void_p())
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_SC_CancelReceiveRequest, [c_void_p])
def scCancelReceiveRequest(terminal_handle):
    pass


@_custom_call(_chirp.CHIRP_SC_RespondToRequest, [c_void_p, c_int, c_void_p, c_uint])
def scRespondToRequest(terminal_handle, operation_id, data):
    buf = create_string_buffer(bytes(data))
    res = _chirp.CHIRP_SC_RespondToRequest(terminal_handle, operation_id, buf, sizeof(buf) - 1)
    if not res:
        raise ErrorCode(res)


@_return_void(_chirp.CHIRP_SC_IgnoreRequest, [c_void_p, c_int])
def scIgnoreRequest(terminal_handle, operation_id):
    pass
