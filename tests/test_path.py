import pychirp
import unittest


class TestPath(unittest.TestCase):
    def test_bad_path(self):
        self.assertRaises(pychirp.BadPath, lambda: pychirp.Path('//'))
        self.assertRaises(pychirp.BadPath, lambda: pychirp.Path('/tmp//'))
        self.assertRaises(pychirp.BadPath, lambda: pychirp.Path('tmp//'))
        self.assertRaises(pychirp.BadPath, lambda: pychirp.Path('a//b'))

    def test_str(self):
        self.assertEqual('/Test', str(pychirp.Path('/Test')))

    def test_len(self):
        self.assertEqual(5, len(pychirp.Path('/Test')))

    def test_eq(self):
        self.assertEqual(pychirp.Path('/Test/tmp'), pychirp.Path('/Test/tmp'))
        self.assertEqual(pychirp.Path('/Test/tmp'), '/Test/tmp')

    def test_truediv(self):
        self.assertEqual(pychirp.Path('/Test/tmp'), pychirp.Path('/Test') / pychirp.Path('tmp'))
        self.assertEqual(pychirp.Path('/Test/tmp'), pychirp.Path('/Test') / 'tmp')
        self.assertRaises(pychirp.BadPath, lambda: pychirp.Path('/Test') / pychirp.Path('/tmp'))

    def test_clear(self):
        path = pychirp.Path('/Test')
        path.clear()
        self.assertEqual(pychirp.Path(), path)

    def test_is_absolute(self):
        self.assertTrue(pychirp.Path('/Test').is_absolute)
        self.assertFalse(pychirp.Path('Test').is_absolute)

    def test_is_root(self):
        self.assertTrue(pychirp.Path('/').is_root)
        self.assertFalse(pychirp.Path('/Test').is_root)
        self.assertFalse(pychirp.Path('').is_root)


if __name__ == '__main__':
    unittest.main()

