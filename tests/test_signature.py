import pychirp
import unittest


class TestSignature(unittest.TestCase):
    def test_init(self):
        sig1 = pychirp.Signature()
        sig2 = pychirp.Signature(123)

    def test_raw(self):
        sig = pychirp.Signature(123)
        self.assertEquals(123, sig.raw)

    def test_comparison(self):
        sig1 = pychirp.Signature(123)
        sig2 = pychirp.Signature(456)
        sig3 = pychirp.Signature(456)
        sig4 = pychirp.Signature()
        sig5 = pychirp.Signature()

        self.assertNotEquals(sig1, 456)
        self.assertNotEquals(sig1, sig2)
        self.assertNotEquals(sig3, sig4)

        self.assertEquals(sig2, 456)
        self.assertEquals(sig4, 0)
        self.assertEquals(sig2, sig3)
        self.assertEquals(sig2, sig3)
        self.assertEquals(sig4, sig5)

    def test_str(self):
        sig = pychirp.Signature(0x12345678)
        self.assertRegex(str(sig), r'.*12345678.*')


if __name__ == '__main__':
    unittest.main()

