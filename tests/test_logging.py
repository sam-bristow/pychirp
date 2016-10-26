import pychirp
import unittest


class TestLogging(unittest.TestCase):
    def test_AppLogger(self):
        pychirp.log_info('Hey dude')

    def test_ComponentLogger(self):
        logger = pychirp.Logger('My Component')
        logger.log_info('Hey dude ', 123, '!')
        logger.log(pychirp.Verbosity.INFO, 'Hello', ' you')

    def test_NonColourised(self):
        pychirp.Logger.app_logger.stdout_verbosity = pychirp.Verbosity.TRACE

        pychirp.log_fatal('FATAL')
        pychirp.log_error('ERROR')
        pychirp.log_warning('WARNING')
        pychirp.log_info('INFO')
        pychirp.log_debug('DEBUG')
        pychirp.log_trace('TRACE')

    def test_Colourised(self):
        pychirp.Logger.colourised_stdout = True
        pychirp.Logger.app_logger.stdout_verbosity = pychirp.Verbosity.TRACE

        pychirp.log_fatal('FATAL')
        pychirp.log_error('ERROR')
        pychirp.log_warning('WARNING')
        pychirp.log_info('INFO')
        pychirp.log_debug('DEBUG')
        pychirp.log_trace('TRACE')

    def test_EffectiveVerbosity(self):
        pychirp.Logger().chirp_verbosity = pychirp.Verbosity.INFO
        pychirp.Logger.max_chirp_verbosity = pychirp.Verbosity.ERROR

        self.assertIs(pychirp.Verbosity.ERROR, pychirp.Logger().effective_chirp_verbosity)
        pychirp.Logger.max_chirp_verbosity = pychirp.Verbosity.DEBUG
        self.assertIs(pychirp.Verbosity.INFO, pychirp.Logger().effective_chirp_verbosity)

        pychirp.Logger().stdout_verbosity = pychirp.Verbosity.INFO
        pychirp.Logger.max_stdout_verbosity = pychirp.Verbosity.ERROR
        self.assertIs(pychirp.Verbosity.ERROR, pychirp.Logger().effective_stdout_verbosity)
        pychirp.Logger.max_stdout_verbosity = pychirp.Verbosity.DEBUG
        self.assertIs(pychirp.Verbosity.INFO, pychirp.Logger().effective_stdout_verbosity)

        pychirp.Logger().chirp_verbosity = pychirp.Verbosity.TRACE
        self.assertIs(pychirp.Verbosity.DEBUG, pychirp.Logger().max_effective_verbosity)

    def test_ProcessInterface(self):
        print('TestLogging.test_ProcessInterface TODO') # TODO

if __name__ == '__main__':
    unittest.main()

