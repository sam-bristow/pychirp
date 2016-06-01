from . import api as _api
from . import object as _object
from . import leaf as _leaf
from .binding import _BindingMixin
import threading as _threading


class _ProtoMessageType:
    PUBLISH = 0
    SCATTER = 1
    GATHER  = 2


class _Terminal(_object.ChirpObject):
    def __init__(self, leaf, terminal_type, name, signature):
        assert isinstance(leaf, _leaf.Leaf)
        assert isinstance(name, str)
        assert isinstance(signature, int)
        self._leaf = leaf
        self._name = name
        self._signature = signature
        super(_Terminal, self).__init__(_api.createTerminal(leaf.handle, terminal_type, name.encode(), signature))

    def _payloadToUserFacingDataType(self, payload, proto_msg_type, payload_complete):
        return payload

    def _userFacingDataTypeToPayload(self, user_facing_data_type, proto_msg_type):
        return user_facing_data_type

    @property
    def leaf(self):
        return self._leaf

    @property
    def name(self):
        return self._name

    @property
    def signature(self):
        return self._signature


class _ManualBindTerminal(_Terminal):
    pass


class _AutoBindTerminal(_BindingMixin, _Terminal):
    def __init__(self, leaf, terminal_type, name, signature):
        _Terminal.__init__(self, leaf, terminal_type, name, signature)
        _BindingMixin.__init__(self)


class _CacheMixin(object):
    def __init__(self, get_cached_message_fn):
        self._get_cached_message_fn = get_cached_message_fn

    def getCachedMessage(self):
        return self._payloadToUserFacingDataType(self._get_cached_message_fn(self.handle), _ProtoMessageType.PUBLISH, True)


class _PublishMixin(object):
    def __init__(self, publish_message_fn):
        self._publish_message_fn = publish_message_fn

    def publishMessage(self, data):
        self._publish_message_fn(self.handle, self._userFacingDataTypeToPayload(data, _ProtoMessageType.PUBLISH))


class _SubscribeMixin(object):
    def __init__(self, async_receive_message_fn):
        self._async_receive_message_fn = async_receive_message_fn
        self._on_message_received = None
        self._pending_message = None
        self._last_received_message = None
        self._cv = _threading.Condition()

        self._async_receive_message_fn(self.handle, self._messageReceivedCompletionHandler)

    def _messageReceivedCompletionHandler(self, err, payload, cached=None):
        if not err:
            data = self._payloadToUserFacingDataType(payload, _ProtoMessageType.PUBLISH, not err)
            with self._cv:
                self._last_received_message = data if cached is None else (data, cached)
                self._pending_message = self._last_received_message

                if self._on_message_received:
                    if cached is None:
                        self._on_message_received(data)
                    else:
                        self._on_message_received(data, cached)

                self._cv.notifyAll()
                self._async_receive_message_fn(self.handle, self._messageReceivedCompletionHandler)

    @property
    def on_message_received(self):
        return self._on_message_received

    @on_message_received.setter
    def on_message_received(self, fn):
        self._on_message_received = fn

    @property
    def last_received_message(self):
        return self._last_received_message

    def waitForMessage(self, timeout=None):
        with self._cv:
            if not self._pending_message and self.is_alive:
                self._cv.wait(timeout)

            msg = self._pending_message
            self._pending_message = None

            if not self.is_alive:
                raise Exception('The object has been destroyed')

            return msg

    def destroy(self):
        super(_SubscribeMixin, self).destroy()
        with self._cv:
            self._cv.notifyAll()

    def tryDestroy(self):
        super(_SubscribeMixin, self).tryDestroy()
        with self._cv:
            self._cv.notifyAll()


class _ServiceMixin(object):
    def __init__(self, async_receive_request_fn, cancel_receive_request_fn, respond_to_request_fn, ignore_request_fn):
        self._async_receive_request_fn = async_receive_request_fn
        self._cancel_receive_request_fn = cancel_receive_request_fn
        self._respond_to_request_fn = respond_to_request_fn
        self._ignore_request_fn = ignore_request_fn
        self._request_handler = None

    def asyncReceiveRequest(self, completion_handler):
        def wrapper(err, operation_id, payload):
            completion_handler(err, operation_id, self._payloadToUserFacingDataType(payload, _ProtoMessageType.SCATTER, not err))
        self._async_receive_request_fn(self.handle, wrapper)

    def cancelReceiveRequest(self):
        self._cancel_receive_request_fn(self.handle)

    def respondToRequest(self, operation_id, data):
        self._respond_to_request_fn(self.handle, operation_id, self._userFacingDataTypeToPayload(data, _ProtoMessageType.GATHER))

    def ignoreRequest(self, operation_id):
        self._ignore_request_fn(self.handle, operation_id)

    def _on_request_received(self, err, operation_id, data):
        response = self._request_handler(err, data)

        if not err:
            if response is None:
                self.ignoreRequest(operation_id)
            else:
                self.respondToRequest(operation_id, response)

        if err.error_code != _api.ErrorCodes.CANCELED:
            self.asyncReceiveRequest(self._on_request_received)

    @property
    def request_handler(self):
        return self._request_handler

    @request_handler.setter
    def request_handler(self, handler_fn):
        self.cancelReceiveRequest()
        self._request_handler = handler_fn
        if handler_fn is not None:
            self.asyncReceiveRequest(self._on_request_received)


class _ClientMixin(object):
    Flags = _api.ScatterGatherFlags
    ControlFlow = _api.ControlFlow

    class Ignored(Exception):
        def __init__(self):
            Exception.__init__(self, 'The service ignored the request')

    class Deaf(Exception):
        def __init__(self):
            Exception.__init__(self, 'The service was not listening for requests')

    class BindingDestroyed(Exception):
        def __init__(self):
            Exception.__init__(self, 'The service\'s binding got destroyed')

    class ConnectionLost(Exception):
        def __init__(self):
            Exception.__init__(self, 'Connection to the service has been lost lost')

    def __init__(self, async_request_fn, cancel_request_fn):
        self._async_request_fn = async_request_fn
        self._cancel_request_fn = cancel_request_fn
        self._cv = _threading.Condition()

    def asyncRequest(self, data, completion_handler):
        def wrapper(err, operation_id, flags, payload):
            data = self._payloadToUserFacingDataType(payload, _ProtoMessageType.SCATTER, not err and not flags & (self.Flags.BINDING_DESTROYED | self.Flags.CONNECTION_LOST | self.Flags.DEAF | self.Flags.IGNORED))
            return completion_handler(err, operation_id, flags, data)
        return self._async_request_fn(self.handle, self._userFacingDataTypeToPayload(data, _ProtoMessageType.SCATTER), wrapper)

    def cancelRequest(self, operation_id):
        self._cancel_request_fn(self.handle, operation_id)

    def request(self, data, only_first_response=False):
        response = {
            'err': None,
            'flags': None,
            'payload': None
        }
        def completion_handler(err, operation_id, flags, payload):
            if err:
                with self._cv:
                    response['err'] = err
                    self._cv.notify_all()
                return self.ControlFlow.STOP

            if only_first_response or flags & self.Flags.FINISHED or not flags & (self.Flags.BINDING_DESTROYED | self.Flags.CONNECTION_LOST | self.Flags.DEAF | self.Flags.IGNORED):
                with self._cv:
                    response['err'] = err
                    response['flags'] = flags
                    response['payload'] = payload
                    self._cv.notify_all()
                return self.ControlFlow.STOP
            else:
                return self.ControlFlow.CONTINUE

        with self._cv:
            operation_id = self._async_request_fn(self.handle, self._userFacingDataTypeToPayload(data, _ProtoMessageType.SCATTER), completion_handler)
            self._cv.wait()

        if response['err']:
            raise response['err']
        if response['flags'] & self.Flags.BINDING_DESTROYED:
            raise self.BindingDestroyed()
        if response['flags'] & self.Flags.CONNECTION_LOST:
            raise self.ConnectionLost()
        if response['flags'] & self.Flags.DEAF:
            raise self.Deaf()
        if response['flags'] & self.Flags.IGNORED:
            raise self.Ignored()

        return self._payloadToUserFacingDataType(response['payload'], _ProtoMessageType.GATHER, True)


class _ProtoTerminalMixin(object):
    def __init__(self, terminal_class, leaf, name, proto_module):
        signature = proto_module.DESCRIPTOR.GetOptions().Extensions[proto_module.signature]
        terminal_class.__init__(self, leaf, name, signature)
        self._proto_module = proto_module

    @property
    def proto_module(self):
        return self._proto_module

    def _payloadToUserFacingDataType(self, payload, proto_msg_type, payload_complete):
        if not payload_complete:
            return payload
        else:
            if proto_msg_type is _ProtoMessageType.PUBLISH:
                msg = self._proto_module.PublishMessage()
            elif proto_msg_type is _ProtoMessageType.SCATTER:
                msg = self._proto_module.ScatterMessage()
            elif proto_msg_type is _ProtoMessageType.GATHER:
                msg = self._proto_module.GatherMessage()
            msg.ParseFromString(bytes(payload))
            return msg

    def _userFacingDataTypeToPayload(self, user_facing_data_type, proto_msg_type):
        return bytearray(user_facing_data_type.SerializeToString())


class _MakePublishMessageMixin(object):
    def makeMessage(self):
        return self.proto_module.PublishMessage()


class _MakeRequestResponseMessagesMixin(object):
    def makeRequestMessage(self):
        return self.proto_module.ScatterMessage()

    def makeResponseMessage(self):
        return self.proto_module.GatherMessage()


class DeafMuteTerminal(_ManualBindTerminal):
    def __init__(self, leaf, name, signature):
        super(DeafMuteTerminal, self).__init__(leaf, _api.TerminalTypes.DEAF_MUTE, name, signature)


class DeafMuteProtoTerminal(_ProtoTerminalMixin, DeafMuteTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, DeafMuteTerminal, leaf, name, proto_module)


class PublishSubscribeTerminal(_PublishMixin, _SubscribeMixin, _ManualBindTerminal):
    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, _api.TerminalTypes.PUBLISH_SUBSCRIBE, name, signature)
        _SubscribeMixin.__init__(self, _api.psAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.psPublish)


class PublishSubscribeProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, PublishSubscribeTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, PublishSubscribeTerminal, leaf, name, proto_module)


class ScatterGatherTerminal(_ServiceMixin, _ClientMixin, _ManualBindTerminal):
    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, _api.TerminalTypes.SCATTER_GATHER, name, signature)
        _ClientMixin.__init__(self, _api.sgAsyncScatterGather, _api.sgCancelScatterGather)
        _ServiceMixin.__init__(self, _api.sgAsyncReceiveScatteredMessage, _api.sgCancelReceiveScatteredMessage, _api.sgRespondToScatteredMessage, _api.sgIgnoreScatteredMessage)


class ScatterGatherProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ScatterGatherTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, ScatterGatherTerminal, leaf, name, proto_module)


class CachedPublishSubscribeTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _ManualBindTerminal):
    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, _api.TerminalTypes.CACHED_PUBLISH_SUBSCRIBE, name, signature)
        _SubscribeMixin.__init__(self, _api.cpsAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.cpsPublish)
        _CacheMixin.__init__(self, _api.cpsGetCachedMessage)


class CachedPublishSubscribeProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedPublishSubscribeTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, CachedPublishSubscribeTerminal, leaf, name, proto_module)


class ProducerTerminal(_PublishMixin, _Terminal):
    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, _api.TerminalTypes.PRODUCER, name, signature)
        _PublishMixin.__init__(self, _api.pcPublish)


class ProducerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, ProducerTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, ProducerTerminal, leaf, name, proto_module)


class ConsumerTerminal(_SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.CONSUMER, name, signature)
        _SubscribeMixin.__init__(self, _api.pcAsyncReceiveMessage)


class ConsumerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, ConsumerTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, ConsumerTerminal, leaf, name, proto_module)


class CachedProducerTerminal(_PublishMixin, _Terminal):
    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, _api.TerminalTypes.CACHED_PRODUCER, name, signature)
        _PublishMixin.__init__(self, _api.cpcPublish)


class CachedProducerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedProducerTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, CachedProducerTerminal, leaf, name, proto_module)


class CachedConsumerTerminal(_CacheMixin, _SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.CACHED_CONSUMER, name, signature)
        _SubscribeMixin.__init__(self, _api.cpcAsyncReceiveMessage)
        _CacheMixin.__init__(self, _api.cpcGetCachedMessage)


class CachedConsumerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedConsumerTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, CachedConsumerTerminal, leaf, name, proto_module)


class MasterTerminal(_PublishMixin, _SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.MASTER, name, signature)
        _SubscribeMixin.__init__(self, _api.msAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.msPublish)


class MasterProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, MasterTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, MasterTerminal, leaf, name, proto_module)


class SlaveTerminal(_PublishMixin, _SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.SLAVE, name, signature)
        _SubscribeMixin.__init__(self, _api.msAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.msPublish)


class SlaveProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, SlaveTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, SlaveTerminal, leaf, name, proto_module)


class CachedMasterTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.CACHED_MASTER, name, signature)
        _SubscribeMixin.__init__(self, _api.cmsAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.cmsPublish)
        _CacheMixin.__init__(self, _api.cmsGetCachedMessage)


class CachedMasterProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedMasterTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, CachedMasterTerminal, leaf, name, proto_module)


class CachedSlaveTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.CACHED_SLAVE, name, signature)
        _SubscribeMixin.__init__(self, _api.cmsAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.cmsPublish)
        _CacheMixin.__init__(self, _api.cmsGetCachedMessage)


class CachedSlaveProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedSlaveTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, CachedSlaveTerminal, leaf, name, proto_module)


class ServiceTerminal(_ServiceMixin, _AutoBindTerminal):
    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, _api.TerminalTypes.SERVICE, name, signature)
        _ServiceMixin.__init__(self, _api.scAsyncReceiveRequest, _api.scCancelReceiveRequest, _api.scRespondToRequest, _api.scIgnoreRequest)


class ServiceProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ServiceTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, ServiceTerminal, leaf, name, proto_module)


class ClientTerminal(_ClientMixin, _Terminal):
    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, _api.TerminalTypes.CLIENT, name, signature)
        _ClientMixin.__init__(self, _api.scAsyncRequest, _api.scCancelRequest)


class ClientProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ClientTerminal):
    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, ClientTerminal, leaf, name, proto_module)
