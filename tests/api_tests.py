from pychirp import api
import unittest
import time


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.resetAsyncData()
        api.initialise()

    def tearDown(self):
        api.shutdown()

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

    def testThrowingExceptions(self):
        with self.assertRaises(api.ErrorCode) as cm:
            api.initialise()
        self.assertLess(cm.exception.error_code, 0)
        self.assertEqual(api.getErrorString(cm.exception.error_code), str(cm.exception))

    def testVersion(self):
        self.assertRegexpMatches(api.getVersion(), r'^\d+\.\d+\.\d+(-[a-zA-Z0-9_-]+)?$')

    def testErrorStrings(self):
        self.assertEqual('Success', api.getErrorString(0))
        self.assertEqual('Unknown internal error occurred', api.getErrorString(-1))

    def testLogFile(self):
        api.setLogFile(b'logfile.log', api.Verbosity.INFO)

    def testSchedulers(self):
        scheduler = api.createScheduler()
        self.assertTrue(scheduler)
        api.setSchedulerThreadPoolSize(scheduler, 3)

    def testDestroy(self):
        scheduler = api.createScheduler()
        api.destroy(scheduler)
        with self.assertRaises(api.ErrorCode) as cm:
            api.destroy(scheduler)

    def testKnownTerminals(self):
        scheduler = api.createScheduler()
        node = api.createNode(scheduler)
        leaf = api.createLeaf(scheduler)
        terminal_a = api.createTerminal(leaf, api.TerminalTypes.DEAF_MUTE, b'Terminal A', 123)
        api.createLocalConnection(node, leaf)
        time.sleep(0.1)

        # wait for new known terminals
        self.resetAsyncData()
        api.asyncAwaitKnownTerminalsChange(node, self.genericCompletionHandler)
        api.createTerminal(leaf, api.TerminalTypes.PUBLISH_SUBSCRIBE, b'Terminal B', 456)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertDictEqual({
            'added'     : True,
            'type'      : 1,
            'name'      : 'Terminal B',
            'signature' : 456
        }, self.async_info)

        # get a list of all known terminals synchronously
        known_terminals = api.getKnownTerminals(node)
        self.assertListEqual([{
            'type'      : 0,
            'name'      : 'Terminal A',
            'signature' : 123
        }, {
            'type'      : 1,
            'name'      : 'Terminal B',
            'signature' : 456
        }], known_terminals)

        # cancel waiting for known terminals to change
        self.resetAsyncData()
        api.asyncAwaitKnownTerminalsChange(node, self.genericCompletionHandler)
        api.cancelAwaitKnownTerminalsChange(node)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        # wait for known terminal to disappear
        self.resetAsyncData()
        api.asyncAwaitKnownTerminalsChange(node, self.genericCompletionHandler)
        api.destroy(terminal_a)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertDictEqual({
            'added'     : False,
            'type'      : 0,
            'name'      : 'Terminal A',
            'signature' : 123
        }, self.async_info)

    def testTcpConnections(self):
        scheduler = api.createScheduler()
        client = api.createTcpClient(scheduler, bytearray(b'security'))

        # check that connect can be canceled
        self.resetAsyncData()
        api.asyncTcpConnect(client, b'127.0.0.1', 63117, None, self.genericCompletionHandler)
        api.cancelTcpConnect(client)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        server = api.createTcpServer(scheduler, b'127.0.0.1', 63117, bytearray(b'security'))

        # check that accept can be canceled
        self.resetAsyncData()
        api.asyncTcpAccept(server, None, self.genericCompletionHandler)
        api.cancelTcpAccept(server)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        # check that connection is established successfully
        self.resetAsyncData()
        api.asyncTcpConnect(client, b'127.0.0.1', 63117, None, self.genericCompletionHandler)
        api.asyncTcpAccept(server, None, self.genericCompletionHandler2)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertIsInstance(self.async_info, api.Handle)
        self.assertTrue(self.async_info)
        client_conn = self.async_info

        self.assertIsNotNone(self.async_err2)
        self.assertFalse(self.async_err2)
        self.assertIsInstance(self.async_info2, api.Handle)
        self.assertTrue(self.async_info2)
        server_conn = self.async_info2

        # check connection properties
        self.assertEqual('127.0.0.1:63117', api.getConnectionDescription(client_conn))
        self.assertEqual(api.getVersion(), api.getRemoteVersion(client_conn))
        self.assertEqual(bytearray(b'security'), api.getRemoteIdentification(client_conn))

        # check assign
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.assignConnection(client_conn, leaf_a, None)
        api.assignConnection(server_conn, leaf_b, None)

        # check await death
        self.resetAsyncData()
        api.asyncAwaitConnectionDeath(client_conn, self.genericCompletionHandler)
        api.cancelAwaitConnectionDeath(client_conn)
        time.sleep(0.1)

        self.assertTrue(self.async_err)

        self.resetAsyncData()
        api.asyncAwaitConnectionDeath(client_conn, self.genericCompletionHandler)
        api.destroy(server_conn)
        time.sleep(0.1)

        self.assertTrue(self.async_err)


    def testBindings(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)

        # get binding state synchronously
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.DEAF_MUTE, b'Terminal A', 123)
        binding_a = api.createBinding(terminal_a, b'Terminal B')
        self.assertFalse(api.getBindingState(binding_a))

        # get binding state asynchronously
        self.resetAsyncData()
        api.asyncGetBindingState(binding_a, self.genericCompletionHandler)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertFalse(self.async_info)

        # wait for the binding's state to change to established
        self.resetAsyncData()
        api.asyncAwaitBindingStateChange(binding_a, self.genericCompletionHandler)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.DEAF_MUTE, b'Terminal B', 123)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertTrue(self.async_info)

        # wait for the binding's state to change to released
        self.resetAsyncData()
        api.asyncAwaitBindingStateChange(binding_a, self.genericCompletionHandler)
        api.destroy(terminal_b)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertFalse(self.async_info)

        # get binding state synchronously
        self.assertFalse(api.getBindingState(binding_a))

        # get binding state asynchronously
        self.resetAsyncData()
        api.asyncGetBindingState(binding_a, self.genericCompletionHandler)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertFalse(self.async_info)

        # cancel waiting for the binding's state to change
        self.resetAsyncData()
        api.asyncAwaitBindingStateChange(binding_a, self.genericCompletionHandler)
        api.cancelAwaitBindingStateChange(binding_a)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

    def testSubscriptions(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)

        # create terminals on both leafs
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.PUBLISH_SUBSCRIBE, b'Terminal A', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.PUBLISH_SUBSCRIBE, b'Terminal B', 123)

        # check the subscription state
        self.assertFalse(api.getSubscriptionState(terminal_a))

        # check the subscription state asynchronously
        self.resetAsyncData()
        api.asyncGetSubscriptionState(terminal_a, self.genericCompletionHandler)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertFalse(self.async_info)

        # create a binding and wait for the subscription state to change to subscribed
        self.resetAsyncData()
        api.asyncAwaitSubscriptionStateChange(terminal_a, self.genericCompletionHandler)
        binding = api.createBinding(terminal_b, b'Terminal A')
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertTrue(self.async_info)

        # check the subscription state
        self.assertTrue(api.getSubscriptionState(terminal_a))

        # destroy the binding and wait for the subscription state to change to unsubscribed
        self.resetAsyncData()
        api.asyncAwaitSubscriptionStateChange(terminal_a, self.genericCompletionHandler)
        api.destroy(binding)
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertFalse(self.async_info)

        # check the subscription state
        self.assertFalse(api.getSubscriptionState(terminal_a))

        # cancel waiting for the subscription state to change
        self.resetAsyncData()
        api.asyncAwaitSubscriptionStateChange(terminal_a, self.genericCompletionHandler)
        api.cancelAwaitSubscriptionStateChange(terminal_a)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

    def testPublishSubscribeTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.PUBLISH_SUBSCRIBE, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.PUBLISH_SUBSCRIBE, b'Multimeter', 123)
        api.createBinding(terminal_b, b'Voltage')
        time.sleep(0.1)

        # cancel receive message operation
        self.resetAsyncData()
        api.psAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.psCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertEqual(bytearray(), self.async_info)

        # successful receive message operation
        self.resetAsyncData()
        api.psAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.psPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertEqual(bytearray([1, 0, 3]), self.async_info)

    def test_ScatterGatherTerminals(self):
        scheduler = api.createScheduler()
        node = api.createNode(scheduler)
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        leaf_c = api.createLeaf(scheduler)
        api.createLocalConnection(node, leaf_a)
        api.createLocalConnection(node, leaf_b)
        api.createLocalConnection(node, leaf_c)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.SCATTER_GATHER, b'Student', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.SCATTER_GATHER, b'Student', 123)
        terminal_c = api.createTerminal(leaf_c, api.TerminalTypes.SCATTER_GATHER, b'Teacher', 123)
        binding_a = api.createBinding(terminal_a, b'Teacher')
        binding_b = api.createBinding(terminal_b, b'Teacher')
        time.sleep(0.1)

        async_scattered = []
        def receiveScatteredMessageCompletionHandler(err, operation_id, payload):
            async_scattered.append({
                'err'          : err,
                'operation_id' : operation_id,
                'payload'      : payload
            })

        async_gathered = []
        def makeScatterGatherCompletionHandler(stop):
            def scatterGatherCompletionHandler(err, operation_id, flags, payload):
                async_gathered.append({
                    'err'          : err,
                    'operation_id' : operation_id,
                    'flags'        : flags,
                    'payload'      : payload
                })
                return api.ControlFlow.STOP if stop else api.ControlFlow.CONTINUE
            return scatterGatherCompletionHandler

        def scatterGather(stopAfterFirstGatherMessage=False):
            while len(async_gathered) > 0:
                async_gathered.pop()
            payload = bytearray([1, 0, 2])
            operation_id = api.sgAsyncScatterGather(terminal_c, payload, makeScatterGatherCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.1)
            return operation_id

        def receiveScatteredMessage():
            while len(async_scattered) > 0:
                async_scattered.pop()
            api.sgAsyncReceiveScatteredMessage(terminal_a, receiveScatteredMessageCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = scatterGather()

        self.assertEqual(2, len(async_gathered))
        self.assertEqual(operation_id, async_gathered[0]['operation_id'])
        self.assertEqual(operation_id, async_gathered[1]['operation_id'])
        self.assertFalse(async_gathered[0]['err'])
        self.assertFalse(async_gathered[1]['err'])
        self.assertEqual(bytearray(), async_gathered[0]['payload'])
        self.assertEqual(bytearray(), async_gathered[1]['payload'])
        self.assertIn(async_gathered[0]['flags'], [api.ScatterGatherFlags.DEAF, api.ScatterGatherFlags.DEAF | api.ScatterGatherFlags.FINISHED])
        self.assertIn(async_gathered[1]['flags'], [api.ScatterGatherFlags.DEAF, api.ScatterGatherFlags.DEAF | api.ScatterGatherFlags.FINISHED])
        self.assertNotEqual(async_gathered[0]['flags'], async_gathered[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received gather messages
        operation_id = scatterGather(True)
        self.assertEqual(1, len(async_gathered))

        # remove a binding so we only receive one gather message from now on
        api.destroy(binding_b)
        time.sleep(0.1)

        # respond to a scattered message
        receiveScatteredMessage()
        operation_id = scatterGather()

        self.assertEqual(1, len(async_scattered))
        self.assertFalse(async_scattered[0]['err'])
        self.assertEqual(bytearray([1, 0, 2]), async_scattered[0]['payload'])
        self.assertTrue(async_scattered[0]['operation_id'])

        api.sgRespondToScatteredMessage(terminal_a, async_scattered[0]['operation_id'], bytearray([2, 0, 3]))
        time.sleep(0.1)

        self.assertEqual(1, len(async_gathered))
        self.assertEqual(operation_id, async_gathered[0]['operation_id'])
        self.assertFalse(async_gathered[0]['err'])
        self.assertEqual(bytearray([2, 0, 3]), async_gathered[0]['payload'])
        self.assertEqual(async_gathered[0]['flags'], api.ScatterGatherFlags.FINISHED)

        # ignore a scattered message
        receiveScatteredMessage()
        operation_id = scatterGather()

        self.assertEqual(1, len(async_scattered))

        api.sgIgnoreScatteredMessage(terminal_a, async_scattered[0]['operation_id'])
        time.sleep(0.1)

        self.assertEqual(1, len(async_gathered))
        self.assertEqual(operation_id, async_gathered[0]['operation_id'])
        self.assertFalse(async_gathered[0]['err'])
        self.assertEqual(bytearray(), async_gathered[0]['payload'])
        self.assertEqual(async_gathered[0]['flags'], api.ScatterGatherFlags.IGNORED | api.ScatterGatherFlags.FINISHED)

        # cancel scatter-gather operation
        receiveScatteredMessage()
        operation_id = scatterGather()
        api.sgCancelScatterGather(terminal_c, operation_id)
        time.sleep(0.1)

        self.assertEqual(1, len(async_gathered))
        self.assertTrue(async_gathered[0]['err'])
        self.assertEqual(bytearray(), async_gathered[0]['payload'])
        self.assertTrue(async_gathered[0]['operation_id'])
        self.assertEqual(async_gathered[0]['flags'], api.ScatterGatherFlags.NO_FLAGS)

        # cancel receive scattered message operation
        receiveScatteredMessage()
        api.sgCancelReceiveScatteredMessage(terminal_a)
        time.sleep(0.1)

        self.assertEqual(1, len(async_scattered))
        self.assertTrue(async_scattered[0]['err'])
        self.assertEqual(bytearray(), async_scattered[0]['payload'])
        self.assertFalse(async_scattered[0]['operation_id'])

    def testCachedPublishSubscribeTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.CACHED_PUBLISH_SUBSCRIBE, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.CACHED_PUBLISH_SUBSCRIBE, b'Multimeter', 123)
        binding_b = api.createBinding(terminal_b, b'Voltage')
        time.sleep(0.1)

        async_data = {}
        def receiveMessageCompletionHandler(err, payload, cached):
            async_data['err']     = err
            async_data['cached']  = cached
            async_data['payload'] = payload

        # cancel receive message operation
        api.cpsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cpsCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray(), async_data['payload'])

        # successful receive message operation
        api.cpsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cpsPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

        # get cached message
        payload = api.cpsGetCachedMessage(terminal_b)
        self.assertEqual(bytearray([1, 0, 3]), payload)

        # receive a cached message
        async_data = {}
        api.destroy(binding_b)
        api.cpsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        binding_b = api.createBinding(terminal_b, b'Voltage')
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertTrue(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

    def testProducerConsumerTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.PRODUCER, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.CONSUMER, b'Voltage', 123)
        time.sleep(0.1)

        # cancel receive message operation
        self.resetAsyncData()
        api.pcAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.pcCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertEqual(bytearray(), self.async_info)

        # successful receive message operation
        self.resetAsyncData()
        api.pcAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.pcPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertEqual(bytearray([1, 0, 3]), self.async_info)

    def testCachedProducerConsumerTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        conn = api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.CACHED_PRODUCER, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.CACHED_CONSUMER, b'Voltage', 123)
        time.sleep(0.1)

        async_data = {}

        def receiveMessageCompletionHandler(err, payload, cached):
            async_data['err'] = err
            async_data['cached'] = cached
            async_data['payload'] = payload

        # cancel receive message operation
        api.cpcAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cpcCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray(), async_data['payload'])

        # successful receive message operation
        api.cpcAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cpcPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

        # get cached message
        payload = api.cpcGetCachedMessage(terminal_b)
        self.assertEqual(bytearray([1, 0, 3]), payload)

        # receive a cached message
        async_data = {}
        api.cpcAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.destroy(conn)
        conn = api.createLocalConnection(leaf_a, leaf_b)
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertTrue(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

    def testMasterSlaveTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.MASTER, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.SLAVE, b'Voltage', 123)
        time.sleep(0.1)

        # cancel receive message operation
        self.resetAsyncData()
        api.msAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.msCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(self.async_err)
        self.assertEqual(bytearray(), self.async_info)

        # successful receive message operation
        self.resetAsyncData()
        api.msAsyncReceiveMessage(terminal_b, self.genericCompletionHandler)
        api.msPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertEqual(bytearray([1, 0, 3]), self.async_info)

    def testCachedMasterSlaveTerminals(self):
        scheduler = api.createScheduler()
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        conn = api.createLocalConnection(leaf_a, leaf_b)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.CACHED_MASTER, b'Voltage', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.CACHED_SLAVE, b'Voltage', 123)
        time.sleep(0.1)

        async_data = {}

        def receiveMessageCompletionHandler(err, payload, cached):
            async_data['err'] = err
            async_data['cached'] = cached
            async_data['payload'] = payload

        # cancel receive message operation
        api.cmsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cmsCancelReceiveMessage(terminal_b)
        time.sleep(0.1)

        self.assertTrue(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray(), async_data['payload'])

        # successful receive message operation
        api.cmsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.cmsPublish(terminal_a, bytearray([1, 0, 3]))
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertFalse(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

        # get cached message
        payload = api.cmsGetCachedMessage(terminal_b)
        self.assertEqual(bytearray([1, 0, 3]), payload)

        # receive a cached message
        async_data = {}
        api.cmsAsyncReceiveMessage(terminal_b, receiveMessageCompletionHandler)
        api.destroy(conn)
        conn = api.createLocalConnection(leaf_a, leaf_b)
        time.sleep(0.1)

        self.assertIsNotNone(async_data['err'])
        self.assertFalse(async_data['err'])
        self.assertTrue(async_data['cached'])
        self.assertEqual(bytearray([1, 0, 3]), async_data['payload'])

    def test_ServiceClientTerminals(self):
        scheduler = api.createScheduler()
        node = api.createNode(scheduler)
        leaf_a = api.createLeaf(scheduler)
        leaf_b = api.createLeaf(scheduler)
        leaf_c = api.createLeaf(scheduler)
        api.createLocalConnection(node, leaf_a)
        api.createLocalConnection(node, leaf_b)
        api.createLocalConnection(node, leaf_c)
        terminal_a = api.createTerminal(leaf_a, api.TerminalTypes.SERVICE, b'Student', 123)
        terminal_b = api.createTerminal(leaf_b, api.TerminalTypes.SERVICE, b'Student', 123)
        terminal_c = api.createTerminal(leaf_c, api.TerminalTypes.CLIENT, b'Student', 123)
        time.sleep(0.1)

        async_requested = []

        def receiveRequestCompletionHandler(err, operation_id, payload):
            async_requested.append({
                'err': err,
                'operation_id': operation_id,
                'payload': payload
            })

        async_responded = []

        def makeRequestCompletionHandler(stop):
            def requestCompletionHandler(err, operation_id, flags, payload):
                async_responded.append({
                    'err': err,
                    'operation_id': operation_id,
                    'flags': flags,
                    'payload': payload
                })
                return api.ControlFlow.STOP if stop else api.ControlFlow.CONTINUE

            return requestCompletionHandler

        def request(stopAfterFirstGatherMessage=False):
            while len(async_responded) > 0:
                async_responded.pop()
            payload = bytearray([1, 0, 2])
            operation_id = api.scAsyncRequest(terminal_c, payload,
                makeRequestCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.1)
            return operation_id

        def receiveRequest():
            while len(async_requested) > 0:
                async_requested.pop()
            api.scAsyncReceiveRequest(terminal_a, receiveRequestCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = request()

        self.assertEqual(2, len(async_responded))
        self.assertEqual(operation_id, async_responded[0]['operation_id'])
        self.assertEqual(operation_id, async_responded[1]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertFalse(async_responded[1]['err'])
        self.assertEqual(bytearray(), async_responded[0]['payload'])
        self.assertEqual(bytearray(), async_responded[1]['payload'])
        self.assertIn(async_responded[0]['flags'], [api.ScatterGatherFlags.DEAF, api.ScatterGatherFlags.DEAF | api.ScatterGatherFlags.FINISHED])
        self.assertIn(async_responded[1]['flags'], [api.ScatterGatherFlags.DEAF, api.ScatterGatherFlags.DEAF | api.ScatterGatherFlags.FINISHED])
        self.assertNotEqual(async_responded[0]['flags'], async_responded[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received requests
        operation_id = request(True)
        self.assertEqual(1, len(async_responded))

        # remove a terminal so we only receive one response from now on
        api.destroy(terminal_b)
        time.sleep(0.1)

        # respond to a request
        receiveRequest()
        operation_id = request()

        self.assertEqual(1, len(async_requested))
        self.assertFalse(async_requested[0]['err'])
        self.assertEqual(bytearray([1, 0, 2]), async_requested[0]['payload'])
        self.assertTrue(async_requested[0]['operation_id'])

        api.scRespondToRequest(terminal_a, async_requested[0]['operation_id'], bytearray([2, 0, 3]))
        time.sleep(0.1)

        self.assertEqual(1, len(async_responded))
        self.assertEqual(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEqual(bytearray([2, 0, 3]), async_responded[0]['payload'])
        self.assertEqual(async_responded[0]['flags'], api.ScatterGatherFlags.FINISHED)

        # ignore a request
        receiveRequest()
        operation_id = request()

        self.assertEqual(1, len(async_requested))

        api.scIgnoreRequest(terminal_a, async_requested[0]['operation_id'])
        time.sleep(0.1)

        self.assertEqual(1, len(async_responded))
        self.assertEqual(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEqual(bytearray(), async_responded[0]['payload'])
        self.assertEqual(async_responded[0]['flags'], api.ScatterGatherFlags.IGNORED | api.ScatterGatherFlags.FINISHED)

        # cancel request operation
        receiveRequest()
        operation_id = request()
        api.scCancelRequest(terminal_c, operation_id)
        time.sleep(0.1)

        self.assertEqual(1, len(async_responded))
        self.assertTrue(async_responded[0]['err'])
        self.assertEqual(bytearray(), async_responded[0]['payload'])
        self.assertTrue(async_responded[0]['operation_id'])
        self.assertEqual(async_responded[0]['flags'], api.ScatterGatherFlags.NO_FLAGS)

        # cancel receive response operation
        receiveRequest()
        api.scCancelReceiveRequest(terminal_a)
        time.sleep(0.1)

        self.assertEqual(1, len(async_requested))
        self.assertTrue(async_requested[0]['err'])
        self.assertEqual(bytearray(), async_requested[0]['payload'])
        self.assertFalse(async_requested[0]['operation_id'])


if __name__ == '__main__':
    unittest.main()
