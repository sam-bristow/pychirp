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

    def tearDown(self):
        try:
            if self.server_connection:
                self.server_connection.destroy()
            if self.client_connection:
                self.client_connection.destroy()
            if self.server:
                self.server.destroy()
            if self.client:
                self.client.destroy()
        except pychirp.Error:
            pass

    def makeConnection(self, identification = None):
        self.client = pychirp.TcpClient(self.scheduler, identification)
        self.server = pychirp.TcpServer(self.scheduler, self.ADDRESS, self.PORT, identification)

        accept_handler_res = None

        def accept_handler(res, connection):
            nonlocal accept_handler_res
            accept_handler_res = res
            self.server_connection = connection

        self.server.async_accept(5.0, accept_handler)

        connect_handler_res = None

        def connect_handler(res, connection):
            nonlocal connect_handler_res
            connect_handler_res = res
            self.client_connection = connection

        self.client.async_connect(self.ADDRESS, self.PORT, 5.0, connect_handler)

        while accept_handler_res is None or connect_handler_res is None:
            pass

        self.assertEquals(pychirp.Success(), accept_handler_res)
        self.assertIsNotNone(self.server_connection)

        self.assertEquals(pychirp.Success(), connect_handler_res)
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


if __name__ == '__main__':
    unittest.main()

