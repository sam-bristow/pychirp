import pychirp
import unittest


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = pychirp.Scheduler()

    def test_set_thread_pool_size(self):
        self.scheduler.set_thread_pool_size(2)
        self.assertRaises(pychirp.Error, lambda: self.scheduler.set_thread_pool_size(1000000))


if __name__ == '__main__':
    unittest.main()

