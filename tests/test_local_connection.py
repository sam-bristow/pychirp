import pychirp
import unittest


class TestLocalConnection(unittest.TestCase):
    def setUp(self):
        self.scheduler = pychirp.Scheduler()
        self.endpointA = pychirp.Leaf(self.scheduler)
        self.endpointB = pychirp.Leaf(self.scheduler)
        self.connection = pychirp.LocalConnection(self.endpointA, self.endpointB)

    def test_init(self):
        pass

    def test_description(self):
        self.assertRegex(self.connection.description, r'.*Local.*')

    def test_remote_version(self):
        self.assertEquals(self.connection.remote_version, pychirp.get_version())

    def test_remote_identification(self):
        self.assertIs(None, self.connection.remote_identification)


if __name__ == '__main__':
    unittest.main()

