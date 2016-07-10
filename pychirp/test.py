from __future__ import print_function
import subprocess
import sys
import time
import tempfile
import traceback
import pkgutil
import importlib
import posixpath
from . import leaf as _leaf
from . import node as _node
from . import scheduler as _scheduler
from . import connection as _connection
from . import terminals as _terminals
from . import tcp as _tcp


def _print(text, end='\n'):
    print(_EscapeSequences.BLUE + 'TEST: ' + text + _EscapeSequences.RESET, end=end)
    sys.stdout.flush()


def _printHeading(text):
    _print(_EscapeSequences.BOLD + _EscapeSequences.UNDERLINE + _EscapeSequences.BLUE + '=====  ' + text + '  =====' + _EscapeSequences.RESET)


def _printInfo(text):
    _print(_EscapeSequences.PINK + text + _EscapeSequences.RESET)


def _printWarning(text):
    _print(_EscapeSequences.YELLOW + text + _EscapeSequences.RESET)


def _printError(text):
    _print(_EscapeSequences.RED + text + _EscapeSequences.RESET)


class _EscapeSequences:
    PINK      = '\033[95m'
    BLUE      = '\033[94m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET     = '\033[0m'


class Failure(Exception):
    def __init__(self, description, errors=[], warnings=[], infos=[]):
        Exception.__init__(self, description)
        self._errors = errors if isinstance(errors, list) else [errors]
        self._warnings = warnings if isinstance(warnings, list) else [warnings]
        self._infos = infos if isinstance(infos, list) else [infos]

    def print(self):
        _printError('FAILURE: ' + str(self))
        for line in self._errors:
            _printError(line)
        for line in self._warnings:
            _printWarning(line)
        for line in self._infos:
            _printInfo(line)

class TestStep(object):
    def __init__(self, description):
        self._description = description

    def __enter__(self):
        _print(self._description + '... ', end='')

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            print(_EscapeSequences.RED + 'FAILED')
        else:
            print(_EscapeSequences.GREEN + 'OK' + _EscapeSequences.RESET)

        if exc_type is Failure:
            exc_val.print()
            idx = -1
            while traceback.extract_tb(exc_tb)[idx].filename == __file__:
                idx -= 1
            info = traceback.extract_tb(exc_tb)[idx]
            _printError('File "{}", line {}'.format(info.filename, info.lineno))
            sys.exit(1)

        sys.stdout.flush()
        return exc_type is Failure


class ProcessTestFixture(object):
    ADDRESS = '127.0.0.1'

    def __init__(self, main_script_filename, configuration_json, proto_package, tcp_port=10000, expected_startup_time=1.0, chirp_location='/PUT'):
        _printHeading('Setting up test fixture')

        self._chirp_location = posixpath.normpath(chirp_location)
        self._scheduler = _scheduler.Scheduler()
        self._node = _node.Node(self._scheduler)
        self._leaf = _leaf.Leaf(self._scheduler)
        self._connection = _connection.LocalConnection(self._node, self._leaf)
        self._tcp_server = _tcp.SimpleTcpServer(self._node, self.ADDRESS, tcp_port, log=None)
        self._proto_modules = {}
        self._mock_terminals = {}

        with TestStep('Writing configuration to file'):
            config_file = tempfile.NamedTemporaryFile('w', delete=False)
            config_file.write(configuration_json)
            config_file.close()

        with TestStep('Starting test process'):
            subprocess.Popen([sys.executable, main_script_filename, '-c', '{}:{}'.format(self.ADDRESS, tcp_port), '-l', chirp_location, config_file.name], shell=True)

        with TestStep('Waiting for test process to connect'):
            self._tcp_server.waitUntilAtLeastOneConnected()

        with TestStep('Waiting {} seconds to ensure process has finished initialising'.format(expected_startup_time)):
            time.sleep(expected_startup_time)

        with TestStep('Loading .proto files for message definitions'):
            for _, module_name, _ in pkgutil.iter_modules(proto_package.__path__):
                module = importlib.import_module(proto_package.__name__ + '.' + module_name)
                self._proto_modules[module.PublishMessage.SIGNATURE] = module

        with TestStep('Creating mock terminals matching the PUT terminals'):
            for terminal in self._node.getKnownTerminals():
                name = terminal['name']
                proto_module = self._proto_modules[terminal['signature']]
                terminal_class = terminal['type'].CounterTerminalType.ProtoTerminalClass
                self._mock_terminals[name] = terminal_class(self._leaf, name, proto_module)

        with TestStep('Waiting until all mock terminals are connected/subscribed'):
            for _, terminal in self._mock_terminals.items():
                if getattr(terminal, 'waitUntilEstablished', None):
                    terminal.waitUntilEstablished()
                if getattr(terminal, 'waitUntilSubscribed', None):
                    terminal.waitUntilSubscribed()

        _printHeading('Running the tests')

    @property
    def leaf(self):
        return self._leaf

    @property
    def mock_terminals(self):
        return self._mock_terminals

    def getVisibleTerminals(self):
        return self._node.getKnownTerminals()

    def getVisibleTerminalsAsFormattedListOfStrings(self, terminals=None):
        if terminals is None:
            terminals = self.getVisibleTerminals()

        max_type_length = max([0] + [len(x['type'].__name__) for x in terminals])

        lines = []
        lines.append('[')
        for terminal in terminals:
            lines.append(("    {{'type': {:" + str(max_type_length+1) + "s} 'signature': 0x{:08x}, 'name': '{}'}},").format(terminal['type'].__name__ + ',', terminal['signature'], terminal['name']))
        lines.append(']')

        return lines

    def printVisibleTerminals(self, terminals=None):
        for line in self.getVisibleTerminalsAsFormattedListOfStrings(terminals):
            print(line)

    def assertEqual(self, actual, expected):
        if actual != expected:
            raise Failure('{} != {}'.format(actual, expected))

    def assertNotEqual(self, actual, expected):
        if actual == expected:
            raise Failure('{} == {}'.format(actual, expected))

    def assertIsNone(self, actual):
        if actual is not None:
            raise Failure('{} is not None'.format(actual))

    def assertIsNotNone(self, actual):
        if actual is None:
            raise Failure('{} is None'.format(actual))

    def assertTrue(self, actual):
        if not actual:
            raise Failure('bool({}) is False'.format(actual))

    def assertFalse(self, actual):
        if actual:
            raise Failure('bool({}) is True'.format(actual))

    def checkVisibleTerminals(self, expected_terminals):
        process_terminals = [
            {'type': _terminals.ProducerTerminal,       'signature': 0x000009cd, 'name': '/Log'},
            {'type': _terminals.ProducerTerminal,       'signature': 0x000009cd, 'name': self._chirp_location + '/Log'},
            {'type': _terminals.CachedProducerTerminal, 'signature': 0x0000040d, 'name': self._chirp_location + '/Errors'},
            {'type': _terminals.CachedProducerTerminal, 'signature': 0x0000040d, 'name': self._chirp_location + '/Warnings'},
            {'type': _terminals.CachedProducerTerminal, 'signature': 0x00000001, 'name': self._chirp_location + '/Operational'}
        ]
        for terminal in process_terminals:
            if terminal not in expected_terminals:
                expected_terminals.append(terminal)

        actual_terminals = self.getVisibleTerminals()
        missing_terminals = [x for x in expected_terminals if x not in actual_terminals]
        unexpected_terminals = [x for x in actual_terminals if x not in expected_terminals]
        if missing_terminals or unexpected_terminals:
            raise Failure('List of expected terminals does not match list of actual terminals',
                          errors=['Missing Terminals:'] + self.getVisibleTerminalsAsFormattedListOfStrings(missing_terminals) +
                                 ['Unexpected Terminals:'] + self.getVisibleTerminalsAsFormattedListOfStrings(unexpected_terminals))

    def checkNotOperational(self, duration=0.0):
        terminal = self._mock_terminals[self._chirp_location + '/Operational']
        if terminal.last_received_message and terminal.last_received_message[0].value:
            raise Failure('The PUT reports being operational')
        for _ in range(int(duration * 100)):
            time.sleep(0.01)
            if terminal.last_received_message and terminal.last_received_message[0].value:
                raise Failure('The PUT reports being operational after initially reporting being non-operational')

    def checkOperational(self, duration=0.0):
        terminal = self._mock_terminals[self._chirp_location + '/Operational']
        if not terminal.last_received_message or not terminal.last_received_message[0].value:
            raise Failure('The PUT reports being non-operational')
        for _ in range(int(duration * 100)):
            time.sleep(0.01)
            if not terminal.last_received_message[0].value:
                raise Failure('The PUT reports being non-operational after initially reporting being operational')
