import pychirp
import unittest
import ctypes


class TestObject(unittest.TestCase):
    def test_init(self):
        obj = pychirp.Object(ctypes.c_void_p())
        scheduler = pychirp.Scheduler()

    def test_destroy(self):
        obj = pychirp.Object(ctypes.c_void_p())
        self.assertRaises(Exception, lambda: obj.destroy())

        scheduler = pychirp.Scheduler()
        scheduler.destroy()
        self.assertRaises(Exception, lambda: scheduler.destroy())

    def test_str(self):
        obj = pychirp.Object(ctypes.c_void_p())
        self.assertRegex(str(obj), r'.*Object.*INVALID.*')
        scheduler = pychirp.Scheduler()
        self.assertRegex(str(scheduler), r'.*Scheduler.*0x[0-9a-f]{8}.*')


if __name__ == '__main__':
    unittest.main()

