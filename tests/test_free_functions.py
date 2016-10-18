import pychirp
import unittest
import os
import tempfile


class TestFreeFunctions(unittest.TestCase):
    def test_get_version(self):
        self.assertRegex(pychirp.get_version(), r'^\d+\.\d+\.\d+(-[a-zA-Z0-9_-]+)?$')

    def test_set_log_file(self):
        filename = tempfile.mktemp(suffix='.log', prefix='chirp-')
        pychirp.set_log_file(filename=filename, verbosity=pychirp.Verbosity.DEBUG)
        self.assertTrue(os.path.isfile(filename))
        self.assertGreater(os.path.getsize(filename), 10)


if __name__ == '__main__':
    unittest.main()

