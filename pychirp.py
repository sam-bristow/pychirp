import ctypes as _ctypes
import platform as _platform
import enum as _enum
import atexit as _atexit


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
# Object class
# ======================================================================================================================
_chirp.CHIRP_Destroy.restype = _api_result_handler
_chirp.CHIRP_Destroy.argtypes = [_ctypes.c_void_p]


class Object:
    def __init__(self, handle: _ctypes.c_void_p):
        self._handle = handle

    def destroy(self) -> None:
        _chirp.CHIRP_Destroy(self._handle)
        self._handle = None

    def __str__(self):
        handleStr = '{:#010x}'.format(self._handle.value) if self._handle.value else 'INVALID'
        return '{} [{}]'.format(self.__class__.__name__, handleStr)


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
