from pychirp.scheduler import *
from pychirp.connection import *
from pychirp.leaf import *
import unittest
import time


# when shutting this down, the program should not crash
class ApiTest(unittest.TestCase):
    def testAutomaticInitialiseAndShutdown(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)

        print('Feel free to kill me. If you do, I should die quietly.')
        print('If you do not kill me, I will terminate in 5 seconds...')
        time.sleep(5)


if __name__ == '__main__':
    unittest.main()
