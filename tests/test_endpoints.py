import pychirp
import unittest


class TestLeaf(unittest.TestCase):
    def setUp(self):
        self.scheduler = pychirp.Scheduler()
        self.leaf = pychirp.Leaf(self.scheduler)

    def test_init(self):
        pass

    def test_scheduler(self):
        self.assertIs(self.scheduler, self.leaf.scheduler)


class TestNode(unittest.TestCase):
    def setUp(self):
        self.scheduler = pychirp.Scheduler()
        self.node = pychirp.Node(self.scheduler)

    def test_init(self):
        pass

    def test_scheduler(self):
        self.assertIs(self.scheduler, self.node.scheduler)


if __name__ == '__main__':
    unittest.main()

