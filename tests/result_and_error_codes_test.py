import pychirp
import unittest


class TestResult(unittest.TestCase):
    def setUp(self):
        self.okResult = pychirp.Result(0)
        self.idResult = pychirp.Result(123)
        self.errorResult = pychirp.Result(-2)

    def test_value(self):
        self.assertEquals(0, self.okResult.value)
        self.assertEquals(123, self.idResult.value)
        self.assertEquals(-2, self.errorResult.value)

    def test_bool(self):
        self.assertTrue(self.okResult)
        self.assertTrue(self.idResult)
        self.assertFalse(self.errorResult)

    def test_comparison(self):
        self.assertNotEqual(self.okResult, self.idResult)
        self.assertEqual(self.idResult, pychirp.Result(123))

    def test_str(self):
        self.assertEqual('[0] Success', str(self.okResult))
        self.assertEqual('[123] Success', str(self.idResult))
        self.assertEqual('[-2] Invalid object handle', str(self.errorResult))


if __name__ == '__main__':
    unittest.main()

