from __future__ import print_function
import argparse as _argparse
import glob as _glob
import json as _json
import logging as _logging
import posixpath as _posixpath
import sys as _sys
import threading as _threading
from . import leaf as _leaf
from . import scheduler as _scheduler
from . import terminals as _terminals
from . import tcp as _tcp
from .proto import chirp_00000001 as _chirp_00000001
from .proto import chirp_000009cd as _chirp_000009cd
from .proto import chirp_0000040d as _chirp_0000040d

DEFAULT_SCHEDULER_THREAD_POOL_SIZE = 2
GLOBAL_LOG_TERMINAL_NAME           = '/Log'
LOGGING_FORMAT                     = '%(asctime)s.%(msecs).03d %(levelname)s - %(message)s'
LOGGING_DATE_FORMAT                = '%d/%m/%Y %H:%M:%S'
LOGGER_NAME                        = 'pychirp'

class ProcessInterface(object):
    instance = None

    def __init__(self, description):
        assert type(self).instance is None, 'You can only instantiate this class once'
        type(self).instance = self
        self._parseCommandLineAndConfiguration(description)
        self._createTerminals()
        self._setupLogging()

    @property
    def connect_target(self):
        return self._connect_target

    @property
    def timeout(self):
        return self._timeout

    @property
    def location(self):
        return self._location

    @property
    def identification(self):
        return self._identification

    @property
    def scheduler(self):
        return self._scheduler

    @property
    def configuration(self):
        return self._configuration

    @property
    def leaf(self):
        return self._leaf

    def getConfigurationValue(self, location, default=None):
        sections = location.split('.')
        thing = self._configuration
        while sections:
            name = sections.pop(0)
            if name in thing:
                thing = thing[name]
            else:
                if default is None:
                    raise Exception('Required configuration value "{}" not found in any configuration files'.format(
                        location))
                else:
                    return default
        return thing

    def start(self):
        self._createTcpClient()

    def _parseCommandLineAndConfiguration(self, description):
        parser = _argparse.ArgumentParser(description=description)
        parser.add_argument('-c, --connect', dest='chirp_connect', type=str, metavar='host:port',
                            help='CHIRP server to connect to (e.g. "hostname:12000")')
        parser.add_argument('-t, --timeout', dest='chirp_timeout', type=int, metavar='ms',
                            help='Connection timeout in milliseconds (-1 for infinity)')
        parser.add_argument('-i, --identification', dest='chirp_identification', type=str, metavar='string',
                            help='Identification for CHIRP connections')
        parser.add_argument('-l, --location', dest='chirp_location', type=str, metavar='path',
                            help='Location of the terminals in the CHIRP terminal tree')
        parser.add_argument('config_files', metavar='config.json', nargs='*',
                            help='Configuration files in JSON format')
        args = parser.parse_args()

        numConfigFiles = 0
        maxFileNameLength = 0
        for pattern in args.config_files:
            for filename in _glob.glob(pattern):
                numConfigFiles += 1
                maxFileNameLength = max(maxFileNameLength, len(filename))

        self._configuration = {}
        print('Reading {} configuration files:'.format(numConfigFiles))
        for pattern in args.config_files:
            for filename in _glob.glob(pattern):
                print(('   {:' + str(maxFileNameLength + 3) + 's}').format(filename + '...'), end='')
                with open(filename) as file:
                    json_data = _json.load(file)
                    self._configuration.update(json_data)
                print(' OK.')
        print('done.')

        if 'chirp' in self._configuration:
            config = self._configuration['chirp']
            if 'connect' in config:
                self._connect_target = config['connect']
            if 'timeout' in config:
                self._timeout = config['timeout']
            if 'location' in config:
                self._location = config['location']
            if 'identification' in config:
                self._identification = config['identification']

        if args.chirp_connect is not None:
            self._connect_target = args.chirp_connect
        if args.chirp_timeout is not None:
            self._timeout = args.chirp_timeout
        if args.chirp_location is not None:
            self._location = args.chirp_location
        if args.chirp_identification is not None:
            self._identification = args.chirp_identification

    def _createTerminals(self):
        self._scheduler = _scheduler.Scheduler(num_threads=DEFAULT_SCHEDULER_THREAD_POOL_SIZE)
        self._leaf = _leaf.Leaf(self._scheduler)
        self._global_log_terminal = _terminals.ProducerProtoTerminal(
            self._leaf, GLOBAL_LOG_TERMINAL_NAME, _chirp_000009cd)
        self._local_log_terminal = _terminals.ProducerProtoTerminal(
            self._leaf, _posixpath.join(self._location, 'Log'), _chirp_000009cd)
        self._errors_terminal = _terminals.CachedProducerProtoTerminal(
            self._leaf, _posixpath.join(self._location, 'Errors'), _chirp_0000040d)
        self._warnings_terminal = _terminals.CachedProducerProtoTerminal(
            self._leaf, _posixpath.join(self._location, 'Warnings'), _chirp_0000040d)
        self._operational_terminal = _terminals.CachedProducerProtoTerminal(
            self._leaf, _posixpath.join(self._location, 'Operational'), _chirp_00000001)

    def _createTcpClient(self):
        if self._connect_target:
            host = self._connect_target.split(':')[0]
            port = int(self._connect_target.split(':')[1])
            self._tcp_client = _tcp.SimpleTcpClient(self._leaf, host, port, self._identification, self._timeout,
                                                    self._logTcp)

    def _logTcp(self, message):
        _logging.getLogger(LOGGER_NAME).info('CHIRP ' + message)

    def _setupLogging(self):
        self._stdout_log_handler = _logging.StreamHandler(stream=_sys.stdout)
        self._stdout_log_handler.setFormatter(_logging.Formatter(LOGGING_FORMAT, LOGGING_DATE_FORMAT))
        self._stdout_log_handler.setLevel(_logging.__dict__[
            self.getConfigurationValue('logging.stdout_level', 'INFO').upper()])

        self._chirp_log_handler = _ChirpLogHandler([self._global_log_terminal, self._local_log_terminal])
        self._chirp_log_handler.setLevel(_logging.__dict__[
            self.getConfigurationValue('logging.stdout_level', 'INFO').upper()])

        self._root_logger = _logging.getLogger()
        self._root_logger.handlers = [self._stdout_log_handler, self._chirp_log_handler]
        self._root_logger.setLevel(_logging.DEBUG)

        for logger_name, level in self.getConfigurationValue('logging.logger_specific_level', {}).items():
            _logging.getLogger(logger_name.upper()).setLevel(_logging.__dict__[level])


class _ChirpLogHandler(_logging.Handler):
    def __init__(self, terminals):
        super(_ChirpLogHandler, self).__init__()
        self._terminals = terminals

    def emit(self, record):
        msg = self._terminals[0].makeMessage()
        msg.timestamp = int(record.created) * 1000000000 + int(record.msecs * 1000000)
        msg.value.first = record.message if hasattr(record, 'message') else record.msg
        msg.value.second = _json.dumps({
            'severity'  : record.levelname,
            'file'      : record.filename,
            'line'      : record.lineno,
            'component' : record.name,
            'func'      : record.funcName
        })

        for terminal in self._terminals:
            terminal.tryPublishMessage(msg)


class DependencyManager(object):
    def __init__(self, leaf, operational_terminal_names, terminals):
        self._lock = _threading.RLock()
        self._terminals = terminals
        self._operational_terminals = []
        self._on_readiness_changed = None
        self._ready = False

        with self._lock:
            for name in operational_terminal_names:
                terminal = _terminals.CachedConsumerProtoTerminal(leaf, name, _chirp_00000001)

                def fn(msg, cached):
                    self._onOperationalMessageReceived(terminal, msg, cached)
                terminal.on_message_received = fn

                self._operational_terminals.append(terminal)
                self._terminals.append(terminal)

            for terminal in self._terminals:
                def fn(state):
                    self._onBindingStateChanged(terminal, state)
                terminal.on_binding_state_changed = fn

    @property
    def ready(self):
        return self._ready

    @property
    def on_readiness_changed(self):
        return self._on_readiness_changed

    @on_readiness_changed.setter
    def on_readiness_changed(self, fn):
        self._on_readiness_changed = fn

    def _collectReadinessInformation(self):
        with self._lock:
            established = [x.is_established for x in self._terminals]
            operational = []
            for terminal in self._operational_terminals:
                operational.append(False)
                try:
                    if terminal.getCachedMessage().value:
                        operational[-1] = True
                except:
                    pass
            return (established, operational)

    def _updateReadiness(self, *_):
        with self._lock:
            established, operational = self._collectReadinessInformation()
            ready = all(established) and all(operational)
            if self._ready != ready:
                self._ready = ready
                if ready:
                    _logging.getLogger(LOGGER_NAME).info('DependencyManager: Dependencies satisfied => READY')
                else:
                    _logging.getLogger(LOGGER_NAME).warning('DependencyManager: Dependencies not satisfied any more')
                if self._on_readiness_changed:
                    self._on_readiness_changed(ready)

    def _onOperationalMessageReceived(self, terminal, msg, cached):
        _logging.getLogger(LOGGER_NAME).debug('DependencyManager: {} changed operational state to {}'.format(
            terminal.name, 'True' if msg.value else 'False'))
        self._updateReadiness()

    def _onBindingStateChanged(self, terminal, state):
        _logging.getLogger(LOGGER_NAME).debug('DependencyManager: {} changed binding state to {}'.format(
            terminal.name, 'ESTABLISHED' if state else 'RELEASED'))
        self._updateReadiness()
