import pychirp
import unittest


class TestTcpConnection(unittest.TestCase):
    ADDRESS = '127.0.0.1'
    PORT = 12345

    def setUp(self):
        self.scheduler = pychirp.Scheduler()
        self.endpointA = pychirp.Leaf(self.scheduler)
        self.endpointB = pychirp.Leaf(self.scheduler)
        self.server = None
        self.server_connection = None
        self.client = None
        self.client_connection = None
        self.connect_handler_res = None
        self.accept_handler_res = None
        self.death_handler_res = None

    def tearDown(self):
        def try_destroy(obj):
            try:
                if obj:
                    obj.destroy()
            except pychirp.Failure:
                pass

        try_destroy(self.server_connection)
        try_destroy(self.client_connection)
        try_destroy(self.server)
        try_destroy(self.client)

    def makeConnection(self, identification = None):
        self.client = pychirp.TcpClient(self.scheduler, identification)
        self.server = pychirp.TcpServer(self.scheduler, self.ADDRESS, self.PORT, identification)

        def accept_handler(res, connection):
            self.accept_handler_res = res
            self.server_connection = connection

        self.server.async_accept(5.0, accept_handler)

        def connect_handler(res, connection):
            self.connect_handler_res = res
            self.client_connection = connection

        self.client.async_connect(self.ADDRESS, self.PORT, 5.0, connect_handler)

        while self.accept_handler_res is None or self.connect_handler_res is None:
            pass

        self.assertEquals(pychirp.Success(), self.accept_handler_res)
        self.assertIsNotNone(self.server_connection)

        self.assertEquals(pychirp.Success(), self.connect_handler_res)
        self.assertIsNotNone(self.client_connection)

    def test_connect_and_getters(self):
        identification = 'abc'
        self.makeConnection(identification)

        self.assertIs(self.scheduler, self.client.scheduler)
        self.assertEqual(identification, self.client.identification)

        self.assertIs(self.scheduler, self.server.scheduler)
        self.assertEqual(self.ADDRESS, self.server.address)
        self.assertEqual(self.PORT, self.server.port)
        self.assertEqual(identification, self.server.identification)

        self.assertEquals(pychirp.get_version(), self.client_connection.remote_version)
        self.assertEquals(identification, self.client_connection.remote_identification)
        self.assertRegex(self.client_connection.description, r'.*' + self.ADDRESS + '.*' + str(self.PORT) + '.*')

        self.assertEquals(pychirp.get_version(), self.server_connection.remote_version)
        self.assertEquals(identification, self.server_connection.remote_identification)
        self.assertRegex(self.server_connection.description, r'.*' + self.ADDRESS + '.*')

    def test_cancel_connect(self):
        self.client = pychirp.TcpClient(self.scheduler)

        def connect_handler(res, connection):
            self.connect_handler_res = res
            self.client_connection = connection

        self.client.async_connect(self.ADDRESS, self.PORT, None, connect_handler)
        self.client.cancel_connect()

        while self.connect_handler_res is None:
            pass

        self.assertEquals(pychirp.Canceled(), self.connect_handler_res)

    def test_cancel_accept(self):
        self.server = pychirp.TcpServer(self.scheduler, self.ADDRESS, self.PORT)

        def accept_handler(res, connection):
            self.accept_handler_res = res
            self.server_connection = connection

        self.server.async_accept(None, accept_handler)
        self.server.cancel_accept()

        while self.accept_handler_res is None:
            pass

        self.assertEquals(pychirp.Canceled(), self.accept_handler_res)

    def test_assign(self):
        self.makeConnection()

        self.server_connection.assign(self.endpointA, None)
        self.client_connection.assign(self.endpointB, None)

        self.assertRaises(pychirp.Failure, lambda: self.server_connection.assign(self.endpointA, None))

    def test_await_death(self):
        self.makeConnection()

        self.server_connection.assign(self.endpointA, 0.05)
        self.client_connection.assign(self.endpointB, 0.05)

        def fn(res):
            self.death_handler_res = res

        self.server_connection.async_await_death(fn)
        self.assertRaises(pychirp.Failure, lambda: self.server_connection.async_await_death(fn))
        self.client_connection.destroy()

        while self.death_handler_res is None:
            pass

        self.assertNotEquals(pychirp.Success(), self.death_handler_res)

    def test_cancel_await_death(self):
        self.makeConnection()

        def fn(res):
            self.death_handler_res = res

        self.server_connection.async_await_death(fn)
        self.server_connection.cancel_await_death()

        while self.death_handler_res is None:
            pass

        self.assertNotEquals(pychirp.Success(), self.death_handler_res)


class TestAutoConnectingTcpClient(unittest.TestCase):
    ADDRESS = TestTcpConnection.ADDRESS
    PORT = TestTcpConnection.PORT

    def setUp(self):
        self.scheduler = pychirp.Scheduler()
        self.endpointA = pychirp.Leaf(self.scheduler)
        self.endpointB = pychirp.Leaf(self.scheduler)
        self.timeout = 5.0
        self.identification = 'hello'
        self.client = pychirp.AutoConnectingTcpClient(self.endpointA, self.ADDRESS, self.PORT, self.timeout,
                                                      self.identification)
        self.server = None
        self.server_connection = None
        self.connect_handler_res = None
        self.connect_handler_connection = None
        self.disconnect_handler_res = None

    def tearDown(self):
        def try_destroy(obj):
            try:
                if obj:
                    obj.destroy()
            except pychirp.Failure:
                pass

        try_destroy(self.server_connection)
        try_destroy(self.server)

        self.client.destroy()

    def test_properties(self):
        self.assertIs(self.endpointA, self.client.endpoint)
        self.assertEquals(self.ADDRESS, self.client.host)
        self.assertEquals(self.PORT, self.client.port)
        self.assertEquals(self.timeout, self.client.timeout)
        self.assertEquals(self.identification, self.client.identification)

    def test_reconnect(self):
        def connFn(res, connection):
            self.connect_handler_connection = connection
            self.connect_handler_res = res

        def discFn(res):
            self.disconnect_handler_res = res

        self.client.connect_observer = connFn
        self.client.disconnect_observer = discFn
        self.client.start()

        # wait for first failed connection attempt
        while self.connect_handler_res is None:
            pass
        self.assertFalse(self.connect_handler_res)

        # create a server that accept the connection
        self.server = pychirp.TcpServer(self.scheduler, self.ADDRESS, self.PORT, self.identification)

        def accept_handler(res, connection):
            print('cool', res)
            self.assertTrue(res)
            self.server_connection = connection
            connection.assign(self.endpointB, self.timeout)

        self.server.async_accept(self.timeout, accept_handler)
        while self.server_connection is None:
            print('Waiting 2')
            import time
            time.sleep(1)
            pass

        # wait until the client establishes the connection
        while not self.connect_handler_res:
            print('Waiting 3')
            import time
            time.sleep(1)
            pass
        self.assertIsNotNone(self.connect_handler_connection)

        # check that the connection has been assigned
        self.assertRaises(pychirp.Failure, lambda: self.connect_handler_connection.assign(self.endpointA, self.timeout))

        # break the connection
        self.assertIsNone(self.disconnect_handler_res)
        self.server_connection.destroy()
        while self.disconnect_handler_res is None:
            print('Waiting 4')
            import time
            time.sleep(1)
            pass

        self.assertFalse(self.disconnect_handler_res)


if __name__ == '__main__':
    unittest.main()

