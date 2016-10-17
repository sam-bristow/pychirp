import ctypes as _ctypes
import platform as _platform
import enum as _enum


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


class Result(object):
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


_chirp.CHIRP_SetLogFile.restype = Result
_chirp.CHIRP_SetLogFile.argtypes = [_ctypes.c_char_p, _ctypes.c_int]


def set_log_file(filename: str, verbosity: Verbosity) -> Result:
    return _chirp.CHIRP_SetLogFile(filename.encode('utf-8'), verbosity.value)
