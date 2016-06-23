from pychirp import api
from pychirp.scheduler import *
from pychirp.leaf import *
from pychirp.connection import *
from pychirp.tcp import *
import unittest
import time


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.resetAsyncData()
        self.scheduler = Scheduler()
        self.leaf_a = Leaf(self.scheduler)
        self.leaf_b = Leaf(self.scheduler)
        self.connection = LocalConnection(self.leaf_a, self.leaf_b)

    def resetAsyncData(self):
        self.async_err = None
        self.async_info = None
        self.async_err2 = None
        self.async_info2 = None

    def genericCompletionHandler(self, err, info=None):
        self.async_err = err
        self.async_info = info

    def genericCompletionHandler2(self, err, info=None):
        self.async_err2 = err
        self.async_info2 = info

    def testTcpConnections(self):
        scheduler = Scheduler()
        client = TcpClient(scheduler, bytearray(b'security'))

        # check that connect can be canceled
        self.resetAsyncData()
        client.asyncConnect('127.0.0.1', 63117, None, self.genericCompletionHandler)
        client.cancelConnect()
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        server = TcpServer(scheduler, '127.0.0.1', 63117, bytearray(b'security'))

        # check that accept can be canceled
        self.resetAsyncData()
        server.asyncAccept(None, self.genericCompletionHandler)
        server.cancelAccept()
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        # check that connection is established successfully
        self.resetAsyncData()
        client.asyncConnect('127.0.0.1', 63117, None, self.genericCompletionHandler)
        server.asyncAccept(None, self.genericCompletionHandler2)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertIsInstance(self.async_info, Connection)
        self.assertTrue(self.async_info)
        client_conn = self.async_info

        self.assertIsNotNone(self.async_err2)
        self.assertFalse(self.async_err2)
        self.assertIsInstance(self.async_info2, Connection)
        self.assertTrue(self.async_info2)
        server_conn = self.async_info2

        # check connection properties
        self.assertEqual('127.0.0.1:63117', client_conn.description)
        self.assertEqual(api.getVersion(), client_conn.remote_version)
        self.assertEqual(bytearray(b'security'), client_conn.remote_identification)

        # check assign
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        client_conn.assign(leaf_a, None)
        server_conn.assign(leaf_b, None)

        # check await death
        self.resetAsyncData()
        client_conn.asyncAwaitDeath(self.genericCompletionHandler)
        client_conn.cancelAwaitDeath()
        time.sleep(0.1)

        self.assertTrue(self.async_err)

        self.resetAsyncData()
        client_conn.asyncAwaitDeath(self.genericCompletionHandler)
        server_conn.destroy()
        time.sleep(0.1)

        self.assertTrue(self.async_err)

    def testSimpleTcpServerAndClient(self):
        # create two leafs
        scheduler_a = Scheduler()
        scheduler_b = Scheduler()
        leaf_a = Leaf(scheduler_a)
        leaf_b = Leaf(scheduler_b)

        # setup the server
        serverConnection = []
        def serverConnectedFn(connection):
            serverConnection.append(connection)

        def serverDisconnectedFn(err, connection):
            del serverConnection[:]

        server = SimpleTcpServer(leaf_a)
        server.on_connected = serverConnectedFn
        server.on_disconnected = serverDisconnectedFn

        self.assertEqual(leaf_a, server.endpoint)
        self.assertIsInstance(server.address, str)
        self.assertIsInstance(server.port, int)
        self.assertEqual(None, server.identification)
        self.assertEqual(None, server.timeout)

        # setup the client
        clientConnection = []
        def clientConnectedFn(connection):
            clientConnection.append(connection)

        def clientDisconnectedFn(err, connection):
            del clientConnection[:]

        client = SimpleTcpClient(leaf_b)
        client.on_connected = clientConnectedFn
        client.on_disconnected = clientDisconnectedFn

        self.assertEqual(leaf_b, client.endpoint)
        self.assertIsInstance(client.host, str)
        self.assertEqual(server.address, client.host)
        self.assertIsInstance(client.port, int)
        self.assertEqual(server.port, client.port)
        self.assertEqual(None, client.identification)
        self.assertEqual(None, client.timeout)

        # check that callbacks are invoked on connect
        server.waitUntilAtLeastOneConnected()
        self.assertTrue(serverConnection)

        client.waitUntilConnected()
        self.assertTrue(clientConnection)

        # check that callbacks are invoked on disconnect
        while True:
            try:
                serverConnection[0].destroy()
                break
            except:
                time.sleep(0.1)

        server.waitUntilAllDisconnected()
        self.assertFalse(serverConnection)
        client.waitUntilDisconnected()
        self.assertFalse(clientConnection)

        # wait until the connection is re-established
        client.waitUntilConnected()
        server.waitUntilAtLeastOneConnected()


if __name__ == '__main__':
    unittest.main()
