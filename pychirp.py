import ctypes as _ctypes
import platform as _platform
import enum as _enum
import atexit as _atexit
import typing as _typing
import threading as _threading
import argparse as _argparse
import glob as _glob
import json as _json
import sys as _sys
import posixpath as _posixpath
import time as _time


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


class Failure(Exception, Result):
    def __init__(self, value: int):
        assert value < 0
        Result.__init__(self, value)

    def __str__(self):
        return Result.__str__(self)


class Canceled(Failure):
    def __init__(self):
        Failure.__init__(self, -12)


class Timeout(Failure):
    def __init__(self):
        Failure.__init__(self, -27)


class Success(Result):
    def __init__(self, value: int = 0):
        assert value >= 0
        Result.__init__(self, value)


def _api_result_handler(result: int) -> Success:
    if result < 0:
        raise Failure(result)
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
            ret = fn(Failure(res), *args[:-1])
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


class _ClassProperty:
    def __init__(self, getter, setter=None):
        self._getter = getter
        self._setter = setter

    def __get__(self, instance, cls=None):
        if cls is None:
            cls = type(instance)
        return self._getter.__get__(instance, cls)()

    def __set__(self, instance, value):
        if not self._setter:
            raise AttributeError("can't set attribute")
        cls = type(instance)
        return self._setter.__get__(instance, cls)(value)

    def setter(self, setter):
        if not isinstance(setter, (classmethod, staticmethod)):
            setter = classmethod(setter)
        self._setter = setter
        return self


def _classproperty(getter):
    if not isinstance(getter, (classmethod, staticmethod)):
        getter = classmethod(getter)
    return _ClassProperty(getter)


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
# Path
# ======================================================================================================================
class BadPath(Exception):
    def __init__(self, path: str):
        self._path = path

    def __str__(self):
        return 'Invalid path: \'{}\''.format(self._path)


class Path:
    def __init__(self, path: _typing.Optional[str] = None):
        self._path = path if path else ''
        if '//' in self._path:
            raise BadPath(self._path)

    def __str__(self):
        return self._path

    def __len__(self):
        return len(self._path)

    def __eq__(self, other):
        return self._path == str(other)

    def __ne__(self, other):
        return not (self == other)

    def __truediv__(self, other):
        if Path(str(other)).is_absolute:
            raise BadPath(str(other))
        return Path(_posixpath.join(self._path, str(other)))

    def clear(self) -> None:
        self._path = ''

    @property
    def is_absolute(self) -> bool:
        return not len(self._path) == 0 and self._path[0] == '/'

    @property
    def is_root(self) -> bool:
        return self._path == '/'


# ======================================================================================================================
# Configuration
# ======================================================================================================================
class BadCommandLine(Exception):
    def __init__(self, description: str):
        self._description = description

    def __str__(self):
        return 'Cannot parse command line: {}'.format(self._description)


class BadConfiguration(Exception):
    def __init__(self, description: str):
        self._description = description

    def __str__(self):
        return 'Cannot parse configuration: {}'.format(self._description)


class Configuration:
    def __init__(self, argv: _typing.Optional[_typing.List[str]] = _sys.argv):
        self._config = {}
        self.update('''
        {
            "chirp": {
                "location": null,
                "connection": {
                    "target": null,
                    "timeout": null,
                    "identification": null
                }
            }
        }
        ''')

        if argv:
            self._parse_cmdline(argv)

    def __str__(self):
        return str(self._config)

    @property
    def config(self) -> _typing.DefaultDict:
        return self._config

    @property
    def location(self) -> Path:
        return Path(self._config['chirp']['location'])

    @property
    def connection_target(self) -> _typing.Optional[str]:
        return self._config['chirp']['connection']['target']

    @property
    def connection_timeout(self) -> _typing.Optional[float]:
        return self._config['chirp']['connection']['timeout']

    @property
    def connection_identification(self) -> _typing.Optional[str]:
        return self._config['chirp']['connection']['identification']

    def update(self, json: str) -> None:
        try:
            def merge(a, b, path=None):
                if path is None:
                    path = []
                for key in b:
                    if key in a:
                        if isinstance(a[key], dict) and isinstance(b[key], dict):
                            merge(a[key], b[key], path + [str(key)])
                        else:
                            a[key] = b[key]
                    else:
                        a[key] = b[key]
                return a

            self._config = merge(self._config, _json.loads(json))
        except Exception as e:
            raise BadConfiguration(str(e))

    def _parse_cmdline(self, argv):
        class ThrowingArgumentParser(_argparse.ArgumentParser):
            def __init__(self):
                _argparse.ArgumentParser.__init__(self)

            def error(self, message):
                raise BadCommandLine(message)

        parser = ThrowingArgumentParser()
        parser.add_argument('--connection_target', '-c', dest='target', type=str, metavar='host:port',
                            help='CHIRP server to connect to (e.g. "hostname:12000")')
        parser.add_argument('--connection_timeout', '-t', dest='timeout', type=float, metavar='seconds',
                            help='Connection timeout in seconds (-1 for infinity)')
        parser.add_argument('--connection_identification', '-i', dest='identification', type=str, metavar='string',
                            help='Identification for CHIRP connections')
        parser.add_argument('--location', '-l', dest='location', type=str, metavar='path',
                            help='Location of the terminals for this process in the CHIRP terminal tree')
        parser.add_argument('--json', '-j', dest='json_overrides', type=str, metavar='JSON', action='append',
                            help='Configuration overrides (in JSON format, e.g. \'{ "my-age": 42 }\')')
        parser.add_argument('config_files', metavar='config.json', nargs='+',
                            help='Configuration files in JSON format')
        pargs = parser.parse_args(argv)

        for pattern in pargs.config_files:
            for filename in _glob.glob(pattern):
                with open(filename, 'r') as file:
                    self.update(file.read())

        if pargs.json_overrides:
            for json_str in pargs.json_overrides:
                self.update(json_str)

        if pargs.location:
            self.update('{"chirp": {"location": "' + pargs.location + '"}}')
        if pargs.target:
            self.update('{"chirp": {"connection": {"target": "' + pargs.target + '"}}}')
        if pargs.timeout:
            self.update('{"chirp": {"connection": {"timeout": ' + str(pargs.timeout) + '}}}')
        if pargs.identification:
            self.update('{"chirp": {"connection": {"identification": "' + pargs.identification + '"}}}')


# ======================================================================================================================
# Timestamp
# ======================================================================================================================
class Timestamp:
    class Precision(_enum.Enum):
        SECONDS = 0
        MILLISECONDS = 1
        MICROSECONDS = 2
        NANOSECONDS = 3

    def __init__(self):
        self._time = _time.time()
        self._ns_since_epoch = int(self._time * 1e9)

    @property
    def ns_since_epoch(self) -> int:
        return self._ns_since_epoch

    @property
    def milliseconds(self):
        return int(self._ns_since_epoch / 1000000) % 1000

    @property
    def microseconds(self):
        return int(self._ns_since_epoch / 1000) % 1000

    @property
    def nanoseconds(self):
        return self._ns_since_epoch % 1000

    def to_string(self, precision: Precision = Precision.MILLISECONDS):
        s = _time.strftime('%d/%m/%Y %T', _time.localtime(int(self._time)))

        if precision.value >= self.Precision.MILLISECONDS.value:
            s += '.{:03}'.format(self.milliseconds)
        if precision.value >= self.Precision.MICROSECONDS.value:
            s += '.{:03}'.format(self.microseconds)
        if precision.value >= self.Precision.NANOSECONDS.value:
            s += '.{:03}'.format(self.nanoseconds)

        return s

    def __str__(self):
        return self.to_string()


# ======================================================================================================================
# Logging
# ======================================================================================================================
class _Verbosities:
    def __init__(self):
        self.stdout = Verbosity.TRACE
        self.chirp = Verbosity.TRACE


if _platform.system() == 'Windows':
    class _Coord(_ctypes.Structure):
        _fields_ = [
            ("X", _ctypes.c_short),
            ("Y", _ctypes.c_short)
        ]


    class _SmallRect(_ctypes.Structure):
        _fields_ = [
            ("Left", _ctypes.c_short),
            ("Top", _ctypes.c_short),
            ("Right", _ctypes.c_short),
            ("Bottom", _ctypes.c_short)
        ]


    class _ConsoleScreenBufferInfo(_ctypes.Structure):
        _fields_ = [
            ("dwSize", _Coord),
            ("dwCursorPosition", _Coord),
            ("wAttributes", _ctypes.c_ushort),
            ("srWindow", _SmallRect),
            ("dwMaximumWindowSize", _SmallRect)
        ]


class Logger:
    _colourised_stdout = False
    _max_verbosities = _Verbosities()
    _logger_verbosities = {}
    _app_logger = None
    _chirp_logger = None
    _lock = _threading.Lock()

    if _platform.system() == 'Windows':
        _STD_OUTPUT_HANDLE = -11
        _win32_stdout_handle = _ctypes.windll.kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
        _win32_original_csbi = _ConsoleScreenBufferInfo()
        _ctypes.windll.kernel32.GetConsoleScreenBufferInfo(_win32_stdout_handle, _ctypes.byref(_win32_original_csbi))
        _win32_original_colours = _win32_original_csbi.wAttributes

    @_classproperty
    def colourised_stdout(cls) -> bool:
        return cls._colourised_stdout

    @colourised_stdout.setter
    def colourised_stdout(cls, enabled: bool):
        cls._colourised_stdout = enabled
        # TODO: notify ProcessInterface to update terminal

    @_classproperty
    def max_stdout_verbosity(cls) -> Verbosity:
        return cls._max_verbosities.stdout

    @max_stdout_verbosity.setter
    def max_stdout_verbosity(cls, verbosity: Verbosity):
        cls._max_verbosities.stdout = verbosity
        # TODO: notify ProcessInterface to update terminal

    @_classproperty
    def max_chirp_verbosity(cls) -> Verbosity:
        return cls._max_verbosities.chirp

    @max_chirp_verbosity.setter
    def max_chirp_verbosity(cls, verbosity: Verbosity):
        cls._max_verbosities.chirp = verbosity

    @_classproperty
    def app_logger(cls):
        return cls._app_logger

    @_classproperty
    def chirp_logger(cls):
        return cls._chirp_logger

    @classmethod
    def _reset_colours(cls):
        if not cls.colourised_stdout or not _sys.stdout.isatty():
            return

        if _platform.system() == 'Windows':
            _ctypes.windll.kernel32.SetConsoleTextAttribute(cls._win32_stdout_handle, cls._win32_original_colours)
        else:
            print('\033[0m', end='')

    @classmethod
    def _set_colour(cls, severity):
        if not cls.colourised_stdout or not _sys.stdout.isatty():
            return

        if _platform.system() == 'Windows':
            colour = {
                Verbosity.TRACE:   6,
                Verbosity.DEBUG:   10,
                Verbosity.INFO:    15,
                Verbosity.WARNING: 14,
                Verbosity.ERROR:   12,
                Verbosity.FATAL:   15 | 64
            }[severity]
            _ctypes.windll.kernel32.SetConsoleTextAttribute(cls._win32_stdout_handle, colour)
        else:
            seq = {
                Verbosity.TRACE:   '\033[22;33m',
                Verbosity.DEBUG:   '\033[01;32m',
                Verbosity.INFO:    '\033[01;37m',
                Verbosity.WARNING: '\033[01;33m',
                Verbosity.ERROR:   '\033[01;31m',
                Verbosity.FATAL:   '\033[41m\033[01;37m'
            }[severity]
            print(seq, end='')

    def __init__(self, component: _typing.Optional[str] = None):
        self._component = component if component else 'app'
        if self._component not in self._logger_verbosities:
            self._verbosities = _Verbosities()
            self._logger_verbosities[self._component] = self._verbosities
        else:
            self._verbosities = self._logger_verbosities[self._component]

    @property
    def component(self) -> str:
        return self._component

    @property
    def stdout_verbosity(self) -> Verbosity:
        return self._verbosities.stdout

    @stdout_verbosity.setter
    def stdout_verbosity(self, verbosity: Verbosity):
        self._verbosities.stdout = verbosity
        # TODO: notify ProcessInterface to update terminal

    @property
    def chirp_verbosity(self) -> Verbosity:
        return self._verbosities.chirp

    @chirp_verbosity.setter
    def chirp_verbosity(self, verbosity: Verbosity):
        self._verbosities.chirp = verbosity
        # TODO: notify ProcessInterface to update terminal

    @property
    def effective_stdout_verbosity(self) -> Verbosity:
        return Verbosity(min(self.max_stdout_verbosity.value, self.stdout_verbosity.value))

    @property
    def effective_chirp_verbosity(self) -> Verbosity:
        return Verbosity(min(self.max_chirp_verbosity.value, self.chirp_verbosity.value))

    @property
    def max_effective_verbosity(self):
        return Verbosity(max(self.effective_stdout_verbosity.value, self.effective_chirp_verbosity.value))

    def log(self, severity: Verbosity, *args):
        timestamp = Timestamp()
        thread_id = _threading.get_ident()

        severity_tag = {
            Verbosity.FATAL:   'TRC',
            Verbosity.ERROR:   'DBG',
            Verbosity.WARNING: 'IFO',
            Verbosity.INFO:    'WRN',
            Verbosity.DEBUG:   'ERR',
            Verbosity.TRACE:   'FAT'
        }[severity]

        if severity.value <= self.effective_stdout_verbosity.value:
            s1 = '{} [T{:05}] '.format(timestamp, thread_id)
            s2 = '{} {}: {}'.format(severity_tag, self._component, ''.join([str(arg) for arg in args]))

            with self._lock:
                self._reset_colours()
                print(s1, end='')
                _sys.stdout.flush()
                self._set_colour(severity)
                print(s2, end='')
                _sys.stdout.flush()
                self._reset_colours()
                print('')
                _sys.stdout.flush()

        if severity.value <= self.effective_chirp_verbosity.value:
            # TODO: log via terminal
            pass

    def log_trace(self, *args):
        self.log(Verbosity.TRACE, *args)

    def log_debug(self, *args):
        self.log(Verbosity.DEBUG, *args)

    def log_info(self, *args):
        self.log(Verbosity.INFO, *args)

    def log_warning(self, *args):
        self.log(Verbosity.WARNING, *args)

    def log_error(self, *args):
        self.log(Verbosity.ERROR, *args)

    def log_fatal(self, *args):
        self.log(Verbosity.FATAL, *args)


Logger._app_logger = Logger()
Logger._chirp_logger = Logger('PyCHIRP')


def log(verbosity: Verbosity, *args):
    Logger.app_logger.log(verbosity, *args)


def log_trace(*args):
    log(Verbosity.TRACE, *args)


def log_debug(*args):
    log(Verbosity.DEBUG, *args)


def log_info(*args):
    log(Verbosity.INFO, *args)


def log_warning(*args):
    log(Verbosity.WARNING, *args)


def log_error(*args):
    log(Verbosity.ERROR, *args)


def log_fatal(*args):
    log(Verbosity.FATAL, *args)


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
                self.destroy()
            except Failure:
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
    def remote_identification(self) -> _typing.Optional[str]:
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

    def assign(self, endpoint: Endpoint, timeout: _typing.Optional[float] = None) -> None:
        _chirp.CHIRP_AssignConnection(self._handle, endpoint._handle, _make_api_timeout(timeout))

    def async_await_death(self, completion_handler: _typing.Callable[[Failure], None]) -> None:
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
    def __init__(self, scheduler: Scheduler, identification: _typing.Optional[str] = None):
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
    def identification(self) -> _typing.Optional[str]:
        return self._identification

    def async_connect(self, host: str, port: int, handshake_timeout: _typing.Optional[float],
                      completion_handler: _typing.Callable[[Result, _typing.Optional[TcpConnection]], None]) -> None:
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
    def __init__(self, scheduler: Scheduler, address: str, port: int, identification: _typing.Optional[str] = None):
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
    def identification(self) -> _typing.Optional[str]:
        return self._identification

    def async_accept(self, handshake_timeout: _typing.Optional[float],
                      completion_handler: _typing.Callable[[Result, _typing.Optional[TcpConnection]], None]) -> None:
        def fn(res, connection_handle):
            connection = None
            if res:
                connection = TcpConnection(_ctypes.cast(connection_handle, _ctypes.c_void_p))
            completion_handler(res, connection)

        _chirp.CHIRP_AsyncTcpAccept(self._handle, _make_api_timeout(handshake_timeout),
                                     _wrap_callback(_chirp.CHIRP_AsyncTcpAccept.argtypes[2], fn), _ctypes.c_void_p())

    def cancel_accept(self) -> None:
        _chirp.CHIRP_CancelTcpAccept(self._handle)


class AutoConnectingTcpClient:
    def __init__(self, endpoint: Endpoint, host: str, port: int, timeout: _typing.Optional[float] = None,
                 identification: _typing.Optional[str] = None):
        # TODO: Allow ProcessInterface and Configuration as ctor parameters
        self._endpoint = endpoint
        self._host = host
        self._port = port
        self._timeout = timeout
        self._identification = identification
        self._connect_observer = None
        self._disconnect_observer = None
        self._client = TcpClient(endpoint.scheduler, identification)
        self._reconnectThread = _threading.Thread(target=self._reconnect_thread_fn)
        self._reconnectThreadInitialised = False
        self._running = False
        self._cv = _threading.Condition()
        self._connection = None

        self._reconnectThread.start()
        with self._cv:
            self._cv.wait_for(lambda: self._reconnectThreadInitialised)

    @property
    def endpoint(self) -> Endpoint:
        return self._endpoint

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def timeout(self) -> _typing.Optional[float]:
        return self._timeout

    @property
    def identification(self) -> _typing.Optional[str]:
        return self._identification

    @property
    def connect_observer(self) -> _typing.Callable[[Result, _typing.Optional[TcpConnection]], None]:
        with self._cv:
            return self._connect_observer

    @connect_observer.setter
    def connect_observer(self, fn: _typing.Callable[[Result, _typing.Optional[TcpConnection]], None]):
        with self._cv:
            self._connect_observer = fn

    @property
    def disconnect_observer(self) -> _typing.Callable[[Failure], None]:
        with self._cv:
            return self._disconnect_observer

    @disconnect_observer.setter
    def disconnect_observer(self, fn: _typing.Callable[[Failure], None]):
        with self._cv:
            self._disconnect_observer = fn

    def _reconnect_thread_fn(self):
        with self._cv:
            self._reconnectThreadInitialised = True
            self._cv.notify()

            while True:
                self._cv.wait()
                if not self._running:
                    return

                if self._connection is not None:
                    self._connection.destroy()
                    self._connection = None

                self._cv.wait(timeout=1.0)
                if not self._running:
                    return

                self._start_connect()

    def _start_connect(self):
        # TODO: logging
        self._client.async_connect(self._host, self._port, self._timeout, self._on_connect_completed)

    def _on_connect_completed(self, res, connection):
        if res == Canceled():
            return

        with self._cv:
            if not self._running:
                return

            if res == Success():
                try:
                    connection.assign(self._endpoint, self._timeout)
                    connection.async_await_death(self._on_connection_died)
                    self._connection = connection

                    # TODO: Logging

                    if self._connect_observer:
                        self._connect_observer(res, connection)

                    return
                except Failure as err:
                    res = err
                    connection.destroy()

            # TODO: Logging

            if self._connect_observer:
                self._connect_observer(res, None)

            self._cv.notify()

    def _on_connection_died(self, err):
        if err == Canceled():
            return

        with self._cv:
            if not self._running:
                return

            # TODO: Logging

            if self._disconnect_observer:
                self._disconnect_observer(err)

            self._cv.notify()

    def start(self):
        with self._cv:
            if self._running:
                raise Exception('Already started')
            if not self._host or not self._port or self._port > 65535:
                raise Exception('Invalid target')

            self._start_connect()
            self._running = True

    def try_start(self) -> bool:
        try:
            self.start()
            return True
        except Failure:
            return False

    def destroy(self) -> None:
        with self._cv:
            self._running = False
            self._cv.notify()

        if self._reconnectThread.isAlive():
            self._reconnectThread.join()

        self._client.destroy()
        self._client = None

        if self._connection:
            self._connection.destroy()
            self._connection = None
            
    def __del__(self):
        if self._client is not None:
            try:
                self.destroy()
            except Failure:
                pass

    def __str__(self):
        if self.host and self.port:
            return '{} connecting to {}:{}'.format(self.__class__.__name__, self.host, self.port)
        else:
            return '{} (disabled)'.format(self.__class__.__name__)


# ======================================================================================================================
# Terminals
# ======================================================================================================================
class _TerminalType(_enum.Enum):
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


class GatherFlags(_enum.Enum):
    NO_FLAGS = 0
    FINISHED = 1 << 0
    IGNORED = 1 << 1
    DEAF = 1 << 2
    BINDING_DESTROYED = 1 << 3
    CONNECTION_LOST = 1 << 4


_chirp.CHIRP_CreateTerminal.restype = _api_result_handler
_chirp.CHIRP_CreateTerminal.argtypes = [_ctypes.POINTER(_ctypes.c_void_p), _ctypes.c_void_p, _ctypes.c_int,
                                        _ctypes.c_char_p, _ctypes.c_uint]


class Terminal(Object):
    def __init__(self, type: _TerminalType, name: str, signature: _typing.Union[Signature, int], *,
                 leaf: _typing.Optional[Leaf] = None):
        # TODO: make leaf parameter use ProcessInterface.leaf by default
        self._leaf = leaf
        self._name = name
        self._signature = signature if isinstance(signature, Signature) else Signature(signature)

        handle = _ctypes.c_void_p()
        _chirp.CHIRP_CreateTerminal(_ctypes.byref(handle), self._leaf._handle, type, self._name.encode('utf-8'),
                                    self._signature.raw)
        Object.__init__(self, handle)

    @property
    def leaf(self) -> Leaf:
        return self._leaf

    @property
    def name(self):
        return self._name

    @property
    def signature(self):
        return self._signature


class PrimitiveTerminal(Terminal):
    def __init__(self, *args, **kwargs):
        Terminal.__init__(self, *args, **kwargs)


class ConvenienceTerminal(Terminal):
    def __init__(self, *args, **kwargs):
        Terminal.__init__(self, *args, **kwargs)


class DeafMuteTerminal(PrimitiveTerminal):
    def __init__(self, name: str, signature: _typing.Union[Signature, int], *, leaf: _typing.Optional[Leaf] = None):
        super(DeafMuteTerminal, self).__init__(_TerminalType.DEAF_MUTE, name, signature, leaf=leaf)


class PublishSubscribeTerminal(PrimitiveTerminal):
    def __init__(self, name: str, signature: _typing.Union[Signature, int], *, leaf: _typing.Optional[Leaf] = None):
        PrimitiveTerminal.__init__(self, _TerminalType.PUBLISH_SUBSCRIBE, name, signature, leaf=leaf)

    def make_message(self):
        pass

    def publish(self, msg):
        pass

    def try_publish(self, msg):
        pass

    def async_receive_message(self, completion_handler):
        pass

    def cancel_receive_message(self):
        pass


class CachedPublishSubscribeTerminal(PrimitiveTerminal):
    def __init__(self, name: str, signature: _typing.Union[Signature, int], *, leaf: _typing.Optional[Leaf] = None):
        PrimitiveTerminal.__init__(self, _TerminalType.CACHED_PUBLISH_SUBSCRIBE, name, signature, leaf=leaf)

    def make_message(self):
        pass

    def publish(self, msg):
        pass

    def try_publish(self, msg):
        pass

    def get_cached_message(self):
        pass

    def async_receive_message(self, completion_handler):
        pass

    def cancel_receive_message(self):
        pass


class ScatterGatherTerminal(PrimitiveTerminal):
    def __init__(self, name: str, signature: _typing.Union[Signature, int], *, leaf: _typing.Optional[Leaf] = None):
        PrimitiveTerminal.__init__(self, _TerminalType.SCATTER_GATHER, name, signature, leaf=leaf)
