from pychirp import api
from pychirp.scheduler import *
from pychirp.node import *
from pychirp.leaf import *
from pychirp.connection import *
from pychirp.binding import *
from pychirp.terminals import *
import proto.chirp_49164
import unittest
import time
import threading


class ObjectOrientedApiTest(unittest.TestCase):
    def setUp(self):
        self.resetAsyncData()

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

    def testSchedulers(self):
        scheduler = Scheduler()
        scheduler.setThreadPoolSize(3)
        scheduler = Scheduler(4)

    def testDestroy(self):
        scheduler = Scheduler()
        scheduler.destroy()
        with self.assertRaises(api.ErrorCode) as cm:
            scheduler.destroy()

    def testKnownTerminals(self):
        scheduler = Scheduler()
        node = Node(scheduler)
        leaf = Leaf(scheduler)
        terminal_a = DeafMuteTerminal(leaf, 'Terminal A', 123)
        connection = LocalConnection(node, leaf)
        time.sleep(0.02)

        # wait for new known terminals
        self.resetAsyncData()
        node.asyncAwaitKnownTerminalsChange(self.genericCompletionHandler)
        terminal_b = PublishSubscribeTerminal(leaf, 'Terminal B', 456)
        time.sleep(0.02)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertDictEqual({
            'added'     : True,
            'type'      : 1,
            'name'      : 'Terminal B',
            'signature' : 456
        }, self.async_info)

        # get a list of all known terminals synchronously
        known_terminals = node.getKnownTerminals()
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
        node.asyncAwaitKnownTerminalsChange(self.genericCompletionHandler)
        node.cancelAwaitKnownTerminalsChange()
        time.sleep(0.02)

        self.assertTrue(self.async_err)
        self.assertIsNone(self.async_info)

        # wait for known terminal to disappear
        self.resetAsyncData()
        node.asyncAwaitKnownTerminalsChange(self.genericCompletionHandler)
        terminal_a.destroy()
        time.sleep(0.02)

        self.assertIsNotNone(self.async_err)
        self.assertFalse(self.async_err)
        self.assertDictEqual({
            'added'     : False,
            'type'      : 0,
            'name'      : 'Terminal A',
            'signature' : 123
        }, self.async_info)

    def testBindings(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = DeafMuteTerminal(leaf_a, 'Terminal A', 123)
        binding = Binding(terminal_a, 'Terminal B')

        self.assertFalse(binding.is_established)

        established = []

        def onEstablished():
            established.append(True)

        binding.on_binding_established = onEstablished

        released = []

        def onReleased():
            released.append(True)

        binding.on_binding_released = onReleased

        changed = []

        def onChanged(is_established):
            changed.append(is_established)

        binding.on_binding_state_changed = onChanged

        terminal_b = DeafMuteTerminal(leaf_b, 'Terminal B', 123)
        binding.waitUntilEstablished()
        self.assertTrue(established)
        self.assertFalse(released)
        self.assertTrue(changed[0])

        del established[:]
        del changed[:]

        terminal_b.destroy()
        binding.waitUntilReleased()
        self.assertFalse(established)
        self.assertTrue(released)
        self.assertFalse(changed[0])

    def testSubscribeMixin(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        consumer = ConsumerProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        producer = ProducerProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        time.sleep(0.02)

        recv_msg = []

        def onMessageReceived(msg, cached=None):
            recv_msg.append((msg, cached))

        consumer.on_message_received = onMessageReceived

        send_msg = producer.makeMessage()
        send_msg.value = 123.456
        producer.publishMessage(send_msg)

        recv_msg.append((consumer.waitForMessage(1.0), None))
        self.assertEquals(123.456, recv_msg[0][0].value)
        self.assertEquals(recv_msg[0], recv_msg[1])
        self.assertEquals(recv_msg[0], (consumer.last_received_message, None))

        consumer = CachedConsumerProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        producer = CachedProducerProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)

        consumer.waitUntilEstablished()
        time.sleep(0.02)

        del recv_msg[:]
        consumer.on_message_received = onMessageReceived

        send_msg = producer.makeMessage()
        send_msg.value = 123.456
        producer.publishMessage(send_msg)

        recv_msg.append(consumer.waitForMessage(1.0))
        self.assertEquals(123.456, recv_msg[0][0].value)
        self.assertEquals(recv_msg[0], recv_msg[1])
        self.assertEquals(recv_msg[0], consumer.last_received_message)

    def testProtoTerminalMixin(self):
        scheduler = Scheduler()
        leaf = Leaf(scheduler)
        terminal = DeafMuteProtoTerminal(leaf, 'Voltage', proto.chirp_49164)

        self.assertEquals(terminal.proto_module, proto.chirp_49164)

    def testDeafMuteTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = DeafMuteTerminal(leaf_a, 'Voltage', 123)
        terminal_b = DeafMuteTerminal(leaf_b, 'Multimeter', 123)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        self.assertTrue(binding_b.is_established)

    def testDeafMuteProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = DeafMuteProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = DeafMuteProtoTerminal(leaf_b, 'Multimeter', proto.chirp_49164)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        self.assertEquals(terminal_a.signature, 49164)
        self.assertTrue(binding_b.is_established)

    def testPublishSubscribeTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = PublishSubscribeTerminal(leaf_a, 'Voltage', 123)
        terminal_b = PublishSubscribeTerminal(leaf_b, 'Multimeter', 123)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals(bytearray([1, 0, 3]), terminal_b.last_received_message)

    def testPublishSubscribeProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = PublishSubscribeProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = PublishSubscribeProtoTerminal(leaf_b, 'Multimeter', proto.chirp_49164)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message.value)

    def testScatterGatherTerminals(self):
        scheduler = Scheduler()
        node = Node(scheduler)
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        leaf_c = Leaf(scheduler)
        connection_a = LocalConnection(node, leaf_a)
        connection_b = LocalConnection(node, leaf_b)
        connection_c = LocalConnection(node, leaf_c)
        terminal_a = ScatterGatherTerminal(leaf_a, 'Student', 123)
        terminal_b = ScatterGatherTerminal(leaf_b, 'Student', 123)
        terminal_c = ScatterGatherTerminal(leaf_c, 'Teacher', 123)
        binding_a = Binding(terminal_a, 'Teacher')
        binding_b = Binding(terminal_b, 'Teacher')
        time.sleep(0.02)

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
                return ScatterGatherTerminal.ControlFlow.STOP if stop else ScatterGatherTerminal.ControlFlow.CONTINUE

            return requestCompletionHandler

        def request(stopAfterFirstGatherMessage=False):
            while len(async_responded) > 0:
                async_responded.pop()
            payload = bytearray([1, 0, 2])
            operation_id = terminal_c.asyncRequest(payload, makeRequestCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.02)
            return operation_id

        def receiveRequest():
            while len(async_requested) > 0:
                async_requested.pop()
            terminal_a.asyncReceiveRequest(receiveRequestCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = request()

        self.assertEquals(2, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertEquals(operation_id, async_responded[1]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertFalse(async_responded[1]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertEquals(bytearray(), async_responded[1]['payload'])
        self.assertIn(async_responded[0]['flags'], [ScatterGatherTerminal.Flags.DEAF, ScatterGatherTerminal.Flags.DEAF | ScatterGatherTerminal.Flags.FINISHED])
        self.assertIn(async_responded[1]['flags'], [ScatterGatherTerminal.Flags.DEAF, ScatterGatherTerminal.Flags.DEAF | ScatterGatherTerminal.Flags.FINISHED])
        self.assertNotEquals(async_responded[0]['flags'], async_responded[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received requests
        operation_id = request(True)
        self.assertEquals(1, len(async_responded))

        # check synchronous methods
        def ignoreHandler(err, payload):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err)
            self.assertEquals(bytearray([3, 4]), payload)

        def respondHandler(err, payload):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err or err.error_code == api.ErrorCodes.CANCELED)
            self.assertEquals(bytearray([3, 4]), payload)
            return payload

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = ignoreHandler

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(bytearray([3, 4]), False)

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(bytearray([3, 4]), True)

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = respondHandler

        response = terminal_c.request(bytearray([3, 4]), False)
        self.assertEquals(bytearray([3, 4]), response)

        terminal_a.request_handler = respondHandler
        terminal_b.request_handler = ignoreHandler

        response = terminal_c.request(bytearray([3, 4]), False)
        self.assertEquals(bytearray([3, 4]), response)

        terminal_a.request_handler = None
        terminal_b.request_handler = None

        # remove a binding so we only receive one response from now on
        binding_b.destroy()
        time.sleep(0.02)

        # respond to a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))
        self.assertFalse(async_requested[0]['err'])
        self.assertEquals(bytearray([1, 0, 2]), async_requested[0]['payload'])
        self.assertTrue(async_requested[0]['operation_id'])

        terminal_a.respondToRequest(async_requested[0]['operation_id'], bytearray([2, 0, 3]))
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray([2, 0, 3]), async_responded[0]['payload'])
        self.assertEquals(async_responded[0]['flags'], api.ScatterGatherFlags.FINISHED)

        # ignore a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))

        terminal_a.ignoreRequest(async_requested[0]['operation_id'])
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertEquals(async_responded[0]['flags'], api.ScatterGatherFlags.IGNORED | api.ScatterGatherFlags.FINISHED)

        # cancel request operation
        receiveRequest()
        operation_id = request()
        terminal_c.cancelRequest(operation_id)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertTrue(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertTrue(async_responded[0]['operation_id'])
        self.assertEquals(async_responded[0]['flags'], api.ScatterGatherFlags.NO_FLAGS)

        # cancel receive response operation
        receiveRequest()
        terminal_a.cancelReceiveRequest()
        time.sleep(0.02)

        self.assertEquals(1, len(async_requested))
        self.assertTrue(async_requested[0]['err'])
        self.assertEquals(bytearray(), async_requested[0]['payload'])
        self.assertFalse(async_requested[0]['operation_id'])

    def testScatterGatherProtoTerminals(self):
        scheduler = Scheduler()
        node = Node(scheduler)
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        leaf_c = Leaf(scheduler)
        connection_a = LocalConnection(node, leaf_a)
        connection_b = LocalConnection(node, leaf_b)
        connection_c = LocalConnection(node, leaf_c)
        terminal_a = ScatterGatherProtoTerminal(leaf_a, 'Student', proto.chirp_49164)
        terminal_b = ScatterGatherProtoTerminal(leaf_b, 'Student', proto.chirp_49164)
        terminal_c = ScatterGatherProtoTerminal(leaf_c, 'Teacher', proto.chirp_49164)
        binding_a = Binding(terminal_a, 'Teacher')
        binding_b = Binding(terminal_b, 'Teacher')
        time.sleep(0.02)

        async_requested = []

        def receiveRequestCompletionHandler(err, operation_id, msg):
            async_requested.append({
                'err': err,
                'operation_id': operation_id,
                'message': msg
            })

        async_responded = []

        def makeRequestCompletionHandler(stop):
            def requestCompletionHandler(err, operation_id, flags, msg):
                async_responded.append({
                    'err': err,
                    'operation_id': operation_id,
                    'flags': flags,
                    'message': msg
                })
                return ClientProtoTerminal.ControlFlow.STOP if stop else ClientProtoTerminal.ControlFlow.CONTINUE

            return requestCompletionHandler

        def request(stopAfterFirstGatherMessage=False):
            while len(async_responded) > 0:
                async_responded.pop()
            msg = terminal_c.makeRequestMessage()
            msg.value = 123.456
            operation_id = terminal_c.asyncRequest(msg, makeRequestCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.02)
            return operation_id

        def receiveRequest():
            while len(async_requested) > 0:
                async_requested.pop()
            terminal_a.asyncReceiveRequest(receiveRequestCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = request()

        self.assertEquals(2, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertEquals(operation_id, async_responded[1]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertFalse(async_responded[1]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertEquals(bytearray(), async_responded[1]['message'])
        self.assertIn(async_responded[0]['flags'], [ClientProtoTerminal.Flags.DEAF, ClientProtoTerminal.Flags.DEAF | ClientProtoTerminal.Flags.FINISHED])
        self.assertIn(async_responded[1]['flags'], [ClientProtoTerminal.Flags.DEAF, ClientProtoTerminal.Flags.DEAF | ClientProtoTerminal.Flags.FINISHED])
        self.assertNotEquals(async_responded[0]['flags'], async_responded[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received requests
        operation_id = request(True)
        self.assertEquals(1, len(async_responded))

        # check synchronous methods
        def ignoreHandler(err, msg):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err)
            self.assertEquals(500, msg.value)

        def respondHandler(err, msg):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err or err.error_code == api.ErrorCodes.CANCELED)
            self.assertEquals(500, msg.value)
            return msg

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = ignoreHandler

        msg = terminal_c.makeRequestMessage()
        msg.value = 500

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(msg, False)

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(msg, True)

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = respondHandler

        response = terminal_c.request(msg, False)
        self.assertEquals(500, response.value)

        terminal_a.request_handler = respondHandler
        terminal_b.request_handler = ignoreHandler

        response = terminal_c.request(msg, False)
        self.assertEquals(500, response.value)

        terminal_a.request_handler = None
        terminal_b.request_handler = None

        # remove a binding so we only receive one response from now on
        binding_b.destroy()
        time.sleep(0.02)

        # respond to a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))
        self.assertFalse(async_requested[0]['err'])
        self.assertEquals(123.456, async_requested[0]['message'].value)
        self.assertTrue(async_requested[0]['operation_id'])

        msg = terminal_a.makeResponseMessage()
        msg.value = 555
        terminal_a.respondToRequest(async_requested[0]['operation_id'], msg)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(555, async_responded[0]['message'].value)
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.FINISHED)

        # ignore a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))

        terminal_a.ignoreRequest(async_requested[0]['operation_id'])
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.IGNORED | ClientProtoTerminal.Flags.FINISHED)

        # cancel request operation
        receiveRequest()
        operation_id = request()
        terminal_c.cancelRequest(operation_id)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertTrue(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertTrue(async_responded[0]['operation_id'])
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.NO_FLAGS)

        # cancel receive response operation
        receiveRequest()
        terminal_a.cancelReceiveRequest()
        time.sleep(0.02)

        self.assertEquals(1, len(async_requested))
        self.assertTrue(async_requested[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertFalse(async_requested[0]['operation_id'])

    def testCachedPublishSubscribeTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedPublishSubscribeTerminal(leaf_a, 'Voltage', 123)
        terminal_b = CachedPublishSubscribeTerminal(leaf_b, 'Multimeter', 123)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        # publish a message
        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), False), terminal_b.last_received_message)

        # get cached message
        payload = terminal_b.getCachedMessage()
        self.assertEquals(bytearray([1, 0, 3]), payload)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), True), terminal_b.last_received_message)

    def testCachedPublishSubscribeProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedPublishSubscribeProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = CachedPublishSubscribeProtoTerminal(leaf_b, 'Multimeter', proto.chirp_49164)
        binding_b = Binding(terminal_b, 'Voltage')
        time.sleep(0.02)

        # publish a message
        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertFalse(terminal_b.last_received_message[1])

        # get cached message
        self.assertEquals(terminal_b.getCachedMessage().value, 123.456)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertTrue(terminal_b.last_received_message[1])

    def testProducerConsumerTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = ProducerTerminal(leaf_a, 'Voltage', 123)
        terminal_b = ConsumerTerminal(leaf_b, 'Voltage', 123)
        time.sleep(0.02)

        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals(bytearray([1, 0, 3]), terminal_b.last_received_message)

    def testProducerConsumerProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = ProducerProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = ConsumerProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        time.sleep(0.02)

        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message.value)

    def testCachedProducerConsumerTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedProducerTerminal(leaf_a, 'Voltage', 123)
        terminal_b = CachedConsumerTerminal(leaf_b, 'Voltage', 123)
        time.sleep(0.02)

        # publish a message
        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), False), terminal_b.last_received_message)

        # get cached message
        payload = terminal_b.getCachedMessage()
        self.assertEquals(bytearray([1, 0, 3]), payload)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), True), terminal_b.last_received_message)

    def testCachedProducerConsumerProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedProducerProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = CachedConsumerProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        time.sleep(0.02)

        # publish a message
        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertFalse(terminal_b.last_received_message[1])

        # get cached message
        self.assertEquals(terminal_b.getCachedMessage().value, 123.456)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertTrue(terminal_b.last_received_message[1])

    def testMasterSlaveTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = MasterTerminal(leaf_a, 'Voltage', 123)
        terminal_b = SlaveTerminal(leaf_b, 'Voltage', 123)
        time.sleep(0.02)

        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals(bytearray([1, 0, 3]), terminal_b.last_received_message)
        self.assertIsNone(terminal_a.last_received_message)

        terminal_b.publishMessage(bytearray([5, 5]))
        time.sleep(0.02)

        self.assertEquals(bytearray([5, 5]), terminal_a.last_received_message)
        self.assertEquals(bytearray([5, 5]), terminal_b.last_received_message)

    def testMasterSlaveProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = MasterProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = SlaveProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        time.sleep(0.02)

        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message.value)
        self.assertIsNone(terminal_a.last_received_message)

        msg.value = 555
        terminal_b.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(555, terminal_a.last_received_message.value)
        self.assertEquals(555, terminal_b.last_received_message.value)

    def testCachedMasterSlaveTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedMasterTerminal(leaf_a, 'Voltage', 123)
        terminal_b = CachedSlaveTerminal(leaf_b, 'Voltage', 123)
        time.sleep(0.02)

        # publish a message on the Master Terminal
        terminal_a.publishMessage(bytearray([1, 0, 3]))
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), False), terminal_b.last_received_message)
        self.assertIsNone(terminal_a.last_received_message)

        # get cached message
        payload = terminal_b.getCachedMessage()
        self.assertEquals(bytearray([1, 0, 3]), payload)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals((bytearray([1, 0, 3]), True), terminal_b.last_received_message)

        # publish a message on the Slave Terminal
        terminal_b.publishMessage(bytearray([5, 5]))
        time.sleep(0.02)

        self.assertEquals((bytearray([5, 5]), False), terminal_a.last_received_message)
        self.assertEquals((bytearray([5, 5]), False), terminal_b.last_received_message)

        # get cached message
        payload = terminal_a.getCachedMessage()
        self.assertEquals(bytearray([5, 5]), payload)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals((bytearray([5, 5]), True), terminal_a.last_received_message)
        self.assertEquals((bytearray([5, 5]), True), terminal_b.last_received_message)

    def testCachedMasterSlaveProtoTerminals(self):
        scheduler = Scheduler()
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        connection = LocalConnection(leaf_a, leaf_b)
        terminal_a = CachedMasterProtoTerminal(leaf_a, 'Voltage', proto.chirp_49164)
        terminal_b = CachedSlaveProtoTerminal(leaf_b, 'Voltage', proto.chirp_49164)
        time.sleep(0.02)

        # publish a message on the Master Terminal
        msg = terminal_a.makeMessage()
        msg.value = 123.456
        terminal_a.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertFalse(terminal_b.last_received_message[1])
        self.assertIsNone(terminal_a.last_received_message)

        # get cached message
        payload = terminal_b.getCachedMessage()
        self.assertEquals(123.456, terminal_b.getCachedMessage().value)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals(123.456, terminal_b.last_received_message[0].value)
        self.assertTrue(terminal_b.last_received_message[1])

        # publish a message on the Slave Terminal
        msg.value = 555
        terminal_b.publishMessage(msg)
        time.sleep(0.02)

        self.assertEquals(555, terminal_a.last_received_message[0].value)
        self.assertFalse(terminal_a.last_received_message[1])
        self.assertEquals(555, terminal_b.last_received_message[0].value)
        self.assertFalse(terminal_b.last_received_message[1])

        # get cached message
        self.assertEquals(555, terminal_a.getCachedMessage().value)
        self.assertEquals(555, terminal_b.getCachedMessage().value)

        # receive a cached message
        connection.destroy()
        connection = LocalConnection(leaf_a, leaf_b)
        time.sleep(0.02)

        self.assertEquals(555, terminal_a.last_received_message[0].value)
        self.assertTrue(terminal_a.last_received_message[1])
        self.assertEquals(555, terminal_b.last_received_message[0].value)
        self.assertTrue(terminal_b.last_received_message[1])

    def testServiceClientTerminals(self):
        scheduler = Scheduler()
        node = Node(scheduler)
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        leaf_c = Leaf(scheduler)
        connection_a = LocalConnection(node, leaf_a)
        connection_b = LocalConnection(node, leaf_b)
        connection_c = LocalConnection(node, leaf_c)
        terminal_a = ServiceTerminal(leaf_a, 'Student', 123)
        terminal_b = ServiceTerminal(leaf_b, 'Student', 123)
        terminal_c = ClientTerminal(leaf_c, 'Student', 123)
        time.sleep(0.02)

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
                return ClientTerminal.ControlFlow.STOP if stop else ClientTerminal.ControlFlow.CONTINUE

            return requestCompletionHandler

        def request(stopAfterFirstGatherMessage=False):
            while len(async_responded) > 0:
                async_responded.pop()
            payload = bytearray([1, 0, 2])
            operation_id = terminal_c.asyncRequest(payload, makeRequestCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.02)
            return operation_id

        def receiveRequest():
            while len(async_requested) > 0:
                async_requested.pop()
            terminal_a.asyncReceiveRequest(receiveRequestCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = request()

        self.assertEquals(2, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertEquals(operation_id, async_responded[1]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertFalse(async_responded[1]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertEquals(bytearray(), async_responded[1]['payload'])
        self.assertIn(async_responded[0]['flags'], [ClientTerminal.Flags.DEAF, ClientTerminal.Flags.DEAF | ClientTerminal.Flags.FINISHED])
        self.assertIn(async_responded[1]['flags'], [ClientTerminal.Flags.DEAF, ClientTerminal.Flags.DEAF | ClientTerminal.Flags.FINISHED])
        self.assertNotEquals(async_responded[0]['flags'], async_responded[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received requests
        operation_id = request(True)
        self.assertEquals(1, len(async_responded))

        # check synchronous methods
        def ignoreHandler(err, payload):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err)
            self.assertEquals(bytearray([3, 4]), payload)

        def respondHandler(err, payload):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err or err.error_code == api.ErrorCodes.CANCELED)
            self.assertEquals(bytearray([3, 4]), payload)
            return payload

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = ignoreHandler

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(bytearray([3, 4]), False)

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(bytearray([3, 4]), True)

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = respondHandler

        response = terminal_c.request(bytearray([3, 4]), False)
        self.assertEquals(bytearray([3, 4]), response)

        terminal_a.request_handler = respondHandler
        terminal_b.request_handler = ignoreHandler

        response = terminal_c.request(bytearray([3, 4]), False)
        self.assertEquals(bytearray([3, 4]), response)

        terminal_a.request_handler = None
        terminal_b.request_handler = None

        # remove a terminal so we only receive one response from now on
        terminal_b.destroy()
        time.sleep(0.02)

        # respond to a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))
        self.assertFalse(async_requested[0]['err'])
        self.assertEquals(bytearray([1, 0, 2]), async_requested[0]['payload'])
        self.assertTrue(async_requested[0]['operation_id'])

        terminal_a.respondToRequest(async_requested[0]['operation_id'], bytearray([2, 0, 3]))
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray([2, 0, 3]), async_responded[0]['payload'])
        self.assertEquals(async_responded[0]['flags'], ClientTerminal.Flags.FINISHED)

        # ignore a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))

        terminal_a.ignoreRequest(async_requested[0]['operation_id'])
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertEquals(async_responded[0]['flags'], ClientTerminal.Flags.IGNORED | ClientTerminal.Flags.FINISHED)

        # cancel request operation
        receiveRequest()
        operation_id = request()
        terminal_c.cancelRequest(operation_id)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertTrue(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['payload'])
        self.assertTrue(async_responded[0]['operation_id'])
        self.assertEquals(async_responded[0]['flags'], ClientTerminal.Flags.NO_FLAGS)

        # cancel receive response operation
        receiveRequest()
        terminal_a.cancelReceiveRequest()
        time.sleep(0.02)

        self.assertEquals(1, len(async_requested))
        self.assertTrue(async_requested[0]['err'])
        self.assertEquals(bytearray(), async_requested[0]['payload'])
        self.assertFalse(async_requested[0]['operation_id'])

    def testServiceClientProtoTerminals(self):
        scheduler = Scheduler()
        node = Node(scheduler)
        leaf_a = Leaf(scheduler)
        leaf_b = Leaf(scheduler)
        leaf_c = Leaf(scheduler)
        connection_a = LocalConnection(node, leaf_a)
        connection_b = LocalConnection(node, leaf_b)
        connection_c = LocalConnection(node, leaf_c)
        terminal_a = ServiceProtoTerminal(leaf_a, 'Student', proto.chirp_49164)
        terminal_b = ServiceProtoTerminal(leaf_b, 'Student', proto.chirp_49164)
        terminal_c = ClientProtoTerminal(leaf_c, 'Student', proto.chirp_49164)
        time.sleep(0.02)

        async_requested = []

        def receiveRequestCompletionHandler(err, operation_id, msg):
            async_requested.append({
                'err': err,
                'operation_id': operation_id,
                'message': msg
            })

        async_responded = []

        def makeRequestCompletionHandler(stop):
            def requestCompletionHandler(err, operation_id, flags, msg):
                async_responded.append({
                    'err': err,
                    'operation_id': operation_id,
                    'flags': flags,
                    'message': msg
                })
                return ClientProtoTerminal.ControlFlow.STOP if stop else ClientProtoTerminal.ControlFlow.CONTINUE

            return requestCompletionHandler

        def request(stopAfterFirstGatherMessage=False):
            while len(async_responded) > 0:
                async_responded.pop()
            msg = terminal_c.makeRequestMessage()
            msg.value = 123.456
            operation_id = terminal_c.asyncRequest(msg, makeRequestCompletionHandler(stopAfterFirstGatherMessage))
            time.sleep(0.02)
            return operation_id

        def receiveRequest():
            while len(async_requested) > 0:
                async_requested.pop()
            terminal_a.asyncReceiveRequest(receiveRequestCompletionHandler)

        # check that the completion handler can be called more than once for a single operation
        operation_id = request()

        self.assertEquals(2, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertEquals(operation_id, async_responded[1]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertFalse(async_responded[1]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertEquals(bytearray(), async_responded[1]['message'])
        self.assertIn(async_responded[0]['flags'], [ClientProtoTerminal.Flags.DEAF, ClientProtoTerminal.Flags.DEAF | ClientProtoTerminal.Flags.FINISHED])
        self.assertIn(async_responded[1]['flags'], [ClientProtoTerminal.Flags.DEAF, ClientProtoTerminal.Flags.DEAF | ClientProtoTerminal.Flags.FINISHED])
        self.assertNotEquals(async_responded[0]['flags'], async_responded[1]['flags'])

        # check that returning STOP from the completion handler stops notifications about received requests
        operation_id = request(True)
        self.assertEquals(1, len(async_responded))

        # check synchronous methods
        def ignoreHandler(err, msg):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err)
            self.assertEquals(500, msg.value)

        def respondHandler(err, msg):
            if err.error_code == api.ErrorCodes.CANCELED:
                return None

            self.assertTrue(not err or err.error_code == api.ErrorCodes.CANCELED)
            self.assertEquals(500, msg.value)
            return msg

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = ignoreHandler

        msg = terminal_c.makeRequestMessage()
        msg.value = 500

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(msg, False)

        with self.assertRaises(ScatterGatherTerminal.Ignored):
            terminal_c.request(msg, True)

        terminal_a.request_handler = ignoreHandler
        terminal_b.request_handler = respondHandler

        response = terminal_c.request(msg, False)
        self.assertEquals(500, response.value)

        terminal_a.request_handler = respondHandler
        terminal_b.request_handler = ignoreHandler

        response = terminal_c.request(msg, False)
        self.assertEquals(500, response.value)

        terminal_a.request_handler = None
        terminal_b.request_handler = None

        # remove a terminal so we only receive one response from now on
        terminal_b.destroy()
        time.sleep(0.02)

        # respond to a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))
        self.assertFalse(async_requested[0]['err'])
        self.assertEquals(123.456, async_requested[0]['message'].value)
        self.assertTrue(async_requested[0]['operation_id'])

        msg = terminal_a.makeResponseMessage()
        msg.value = 555
        terminal_a.respondToRequest(async_requested[0]['operation_id'], msg)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(555, async_responded[0]['message'].value)
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.FINISHED)

        # ignore a request
        receiveRequest()
        operation_id = request()

        self.assertEquals(1, len(async_requested))

        terminal_a.ignoreRequest(async_requested[0]['operation_id'])
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertEquals(operation_id, async_responded[0]['operation_id'])
        self.assertFalse(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.IGNORED | ClientProtoTerminal.Flags.FINISHED)

        # cancel request operation
        receiveRequest()
        operation_id = request()
        terminal_c.cancelRequest(operation_id)
        time.sleep(0.02)

        self.assertEquals(1, len(async_responded))
        self.assertTrue(async_responded[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertTrue(async_responded[0]['operation_id'])
        self.assertEquals(async_responded[0]['flags'], ClientProtoTerminal.Flags.NO_FLAGS)

        # cancel receive response operation
        receiveRequest()
        terminal_a.cancelReceiveRequest()
        time.sleep(0.02)

        self.assertEquals(1, len(async_requested))
        self.assertTrue(async_requested[0]['err'])
        self.assertEquals(bytearray(), async_responded[0]['message'])
        self.assertFalse(async_requested[0]['operation_id'])


if __name__ == '__main__':
    unittest.main()
