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

    def tryPublishMessage(self, data):
        try:
            self.publishMessage(data)
            return True
        except:
            return False


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


class _SubscribableMixin(object):
    def __init__(self):
        self._on_subscribed = None
        self._on_unsubscribed = None
        self._on_subscription_state_changed = None
        self._is_subscribed = False
        self._subscription_cv = _threading.Condition()

        _api.asyncGetSubscriptionState(self.handle, self._subscriptionStateCompletionHandler)

    def _subscriptionStateCompletionHandler(self, err, is_established):
        if not err:
            with self._subscription_cv:
                if self._is_subscribed != is_established:
                    self._is_subscribed = is_established

                    if self._on_subscription_state_changed:
                        self._on_subscription_state_changed(is_established)

                    fn = self._on_subscribed if is_established else self._on_unsubscribed
                    if fn:
                        fn()

                    self._subscription_cv.notifyAll()
                if self.handle:
                    try:
                        _api.asyncAwaitSubscriptionStateChange(self.handle, self._subscriptionStateCompletionHandler)
                    except:
                        pass

    @property
    def on_subscribed(self):
        return self._on_subscribed

    @on_subscribed.setter
    def on_subscribed(self, fn):
        self._on_subscribed = fn

    @property
    def on_unsubscribed(self):
        return self._on_unsubscribed

    @on_unsubscribed.setter
    def on_unsubscribed(self, fn):
        self._on_unsubscribed = fn

    @property
    def on_subscription_state_changed(self):
        return self._on_subscription_state_changed

    @on_subscription_state_changed.setter
    def on_subscription_state_changed(self, fn):
        self._on_subscription_state_changed = fn

    @property
    def is_subscribed(self):
        return self._is_subscribed

    def _waitUntilSubscriptionState(self, state):
        with self._subscription_cv:
            while self._is_subscribed != state and self.is_alive:
                self._subscription_cv.wait()
            if not self.is_alive:
                raise Exception('The object has been destroyed')

    def waitUntilSubscribed(self):
        self._waitUntilSubscriptionState(True)

    def waitUntilUnsubscribed(self):
        self._waitUntilSubscriptionState(False)

    def destroy(self):
        super(_SubscribableMixin, self).destroy()
        with self._subscription_cv:
            self._subscription_cv.notifyAll()

    def tryDestroy(self):
        if not super(_SubscribableMixin, self).tryDestroy():
            return False
        with self._subscription_cv:
            self._subscription_cv.notifyAll()
        return True


class _GatherOrServiceMixin(object):
    def __init__(self, async_receive_scattered_message_fn, cancel_receive_scattered_message_fn, respond_to_scattered_message_fn, ignore_scattered_message_fn):
        self._async_receive_scattered_message_fn = async_receive_scattered_message_fn
        self._cancel_receive_scattered_message_fn = cancel_receive_scattered_message_fn
        self._respond_to_scattered_message_fn = respond_to_scattered_message_fn
        self._ignore_scattered_message_fn = ignore_scattered_message_fn
        self._scattered_message_handler_fn = None

    def _asyncReceiveScatteredMessage(self, completion_handler):
        def wrapper(err, operation_id, payload):
            completion_handler(err, operation_id, self._payloadToUserFacingDataType(payload, _ProtoMessageType.SCATTER, not err))
        self._async_receive_scattered_message_fn(self.handle, wrapper)

    def _cancelReceiveScatteredMessage(self):
        self._cancel_receive_scattered_message_fn(self.handle)

    def _respondToScatteredMessage(self, operation_id, data):
        self._respond_to_scattered_message_fn(self.handle, operation_id, self._userFacingDataTypeToPayload(data, _ProtoMessageType.GATHER))

    def _ignoreScatteredMessage(self, operation_id):
        self._ignore_scattered_message_fn(self.handle, operation_id)

    def _on_scattered_message_received(self, err, operation_id, data):
        response = self._scattered_message_handler_fn(err, data)

        if not err:
            if response is None:
                self._ignoreScatteredMessage(operation_id)
            else:
                self._respondToScatteredMessage(operation_id, response)

        if err.error_code != _api.ErrorCodes.CANCELED:
            self._asyncReceiveScatteredMessage(self._on_scattered_message_received)

    @property
    def _scattered_message_handler(self):
        return self._scattered_message_handler_fn

    @_scattered_message_handler.setter
    def _scattered_message_handler(self, handler_fn):
        self._cancelReceiveScatteredMessage()
        self._scattered_message_handler_fn = handler_fn
        if handler_fn is not None:
            self._asyncReceiveScatteredMessage(self._on_scattered_message_received)


class _GatherMixin(_GatherOrServiceMixin):
    def __init__(self, async_receive_scattered_message_fn, cancel_receive_scattered_message_fn, respond_to_scattered_message_fn, ignore_scattered_message_fn):
        _GatherOrServiceMixin.__init__(self, async_receive_scattered_message_fn, cancel_receive_scattered_message_fn, respond_to_scattered_message_fn, ignore_scattered_message_fn)

    def asyncReceiveScatteredMessage(self, completion_handler):
        self._asyncReceiveScatteredMessage(completion_handler)

    def cancelReceiveScatteredMessage(self):
        self._cancelReceiveScatteredMessage()

    def respondToScatteredMessage(self, operation_id, data):
        self._respondToScatteredMessage(operation_id, data)

    def ignoreScatteredMessage(self, operation_id):
        self._ignoreScatteredMessage(operation_id)

    @property
    def scattered_message_handler(self):
        return self._scattered_message_handler

    @scattered_message_handler.setter
    def scattered_message_handler(self, handler_fn):
        self._scattered_message_handler = handler_fn


class _ServiceMixin(_GatherOrServiceMixin):
    def __init__(self, async_receive_request_fn, cancel_receive_request_fn, respond_to_request_fn, ignore_request_fn):
        _GatherOrServiceMixin.__init__(self, async_receive_request_fn, cancel_receive_request_fn, respond_to_request_fn, ignore_request_fn)

    def asyncReceiveRequest(self, completion_handler):
        self._asyncReceiveScatteredMessage(completion_handler)

    def cancelReceiveRequest(self):
        self._cancelReceiveScatteredMessage()

    def respondToRequest(self, operation_id, data):
        self._respondToScatteredMessage(operation_id, data)

    def ignoreRequest(self, operation_id):
        self._ignoreScatteredMessage(operation_id)

    @property
    def request_handler(self):
        return self._scattered_message_handler

    @request_handler.setter
    def request_handler(self, handler_fn):
        self._scattered_message_handler = handler_fn


class _ScatterOrClientMixin(object):
    Flags = _api.ScatterGatherFlags
    ControlFlow = _api.ControlFlow

    class Ignored(Exception):
        def __init__(self):
            Exception.__init__(self, 'The remote terminal ignored the request')

    class Deaf(Exception):
        def __init__(self):
            Exception.__init__(self, 'The remote terminal was not listening for requests')

    class BindingDestroyed(Exception):
        def __init__(self):
            Exception.__init__(self, 'The remote terminal\'s binding got destroyed')

    class ConnectionLost(Exception):
        def __init__(self):
            Exception.__init__(self, 'Connection to the remote terminal has been lost lost')

    def __init__(self, async_scatter_gather_fn, cancel_scatter_gather_fn):
        self._async_scatter_gather_fn = async_scatter_gather_fn
        self._cancel_scatter_gather_fn = cancel_scatter_gather_fn
        self._cv = _threading.Condition()

    def _asyncScatterGather(self, data, completion_handler):
        def wrapper(err, operation_id, flags, payload):
            data = self._payloadToUserFacingDataType(payload, _ProtoMessageType.SCATTER, not err and not flags & (self.Flags.BINDING_DESTROYED | self.Flags.CONNECTION_LOST | self.Flags.DEAF | self.Flags.IGNORED))
            return completion_handler(err, operation_id, flags, data)
        return self._async_scatter_gather_fn(self.handle, self._userFacingDataTypeToPayload(data, _ProtoMessageType.SCATTER), wrapper)

    def _cancelScatterGather(self, operation_id):
        self._cancel_scatter_gather_fn(self.handle, operation_id)

    def _scatterGather(self, data, only_first_response=False):
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
            operation_id = self._async_scatter_gather_fn(self.handle, self._userFacingDataTypeToPayload(data, _ProtoMessageType.SCATTER), completion_handler)
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


class _ScatterMixin(_ScatterOrClientMixin):
    def __init__(self, async_scatter_gather_fn, cancel_scatter_gather_fn):
        _ScatterOrClientMixin.__init__(self, async_scatter_gather_fn, cancel_scatter_gather_fn)

    def asyncScatterGather(self, data, completion_handler):
        return self._asyncScatterGather(data, completion_handler)

    def cancelScatterGather(self, operation_id):
        self._cancelScatterGather(operation_id)

    def scatterGather(self, data, only_first_response=False):
        return self._scatterGather(data, only_first_response)


class _ClientMixin(_ScatterOrClientMixin):
    def __init__(self, async_request_fn, cancel_request_fn):
        _ScatterOrClientMixin.__init__(self, async_request_fn, cancel_request_fn)

    def asyncRequest(self, data, completion_handler):
        return self._asyncScatterGather(data, completion_handler)

    def cancelRequest(self, operation_id):
        self._cancelScatterGather(operation_id)

    def request(self, data, only_first_response=False):
        return self._scatterGather(data, only_first_response)


class _ProtoTerminalMixin(object):
    def __init__(self, leaf, name, proto_module):
        signature = proto_module.PublishMessage.SIGNATURE
        self.TerminalClass.__init__(self, leaf, name, signature)
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
    TERMINAL_TYPE = _api.TerminalTypes.DEAF_MUTE

    def __init__(self, leaf, name, signature):
        super(DeafMuteTerminal, self).__init__(leaf, self.TERMINAL_TYPE, name, signature)


class DeafMuteProtoTerminal(_ProtoTerminalMixin, DeafMuteTerminal):
    TerminalClass = DeafMuteTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


DeafMuteTerminal.CounterTerminalType = DeafMuteTerminal
DeafMuteTerminal.ProtoTerminalClass = DeafMuteProtoTerminal


class PublishSubscribeTerminal(_PublishMixin, _SubscribeMixin, _SubscribableMixin, _ManualBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.PUBLISH_SUBSCRIBE

    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _SubscribeMixin.__init__(self, _api.psAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.psPublish)


class PublishSubscribeProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, PublishSubscribeTerminal):
    TerminalClass = PublishSubscribeTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


PublishSubscribeTerminal.CounterTerminalType = PublishSubscribeTerminal
PublishSubscribeTerminal.ProtoTerminalClass = PublishSubscribeProtoTerminal


class ScatterGatherTerminal(_ScatterMixin, _GatherMixin, _SubscribableMixin, _ManualBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.SCATTER_GATHER

    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _ScatterMixin.__init__(self, _api.sgAsyncScatterGather, _api.sgCancelScatterGather)
        _GatherMixin.__init__(self, _api.sgAsyncReceiveScatteredMessage, _api.sgCancelReceiveScatteredMessage, _api.sgRespondToScatteredMessage, _api.sgIgnoreScatteredMessage)


class ScatterGatherProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ScatterGatherTerminal):
    TerminalClass = ScatterGatherTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


ScatterGatherTerminal.CounterTerminalType = ScatterGatherTerminal
ScatterGatherTerminal.ProtoTerminalClass = ScatterGatherProtoTerminal


class CachedPublishSubscribeTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _SubscribableMixin, _ManualBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.CACHED_PUBLISH_SUBSCRIBE

    def __init__(self, leaf, name, signature):
        _ManualBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribeMixin.__init__(self, _api.cpsAsyncReceiveMessage)
        _SubscribableMixin.__init__(self)
        _PublishMixin.__init__(self, _api.cpsPublish)
        _CacheMixin.__init__(self, _api.cpsGetCachedMessage)


class CachedPublishSubscribeProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedPublishSubscribeTerminal):
    TerminalClass = CachedPublishSubscribeTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


CachedPublishSubscribeTerminal.CounterTerminalType = CachedPublishSubscribeTerminal
CachedPublishSubscribeTerminal.ProtoTerminalClass = CachedPublishSubscribeProtoTerminal


class ProducerTerminal(_PublishMixin, _SubscribableMixin, _Terminal):
    TERMINAL_TYPE = _api.TerminalTypes.PRODUCER

    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _PublishMixin.__init__(self, _api.pcPublish)


class ProducerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, ProducerTerminal):
    TerminalClass = ProducerTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


ProducerTerminal.ProtoTerminalClass = ProducerProtoTerminal


class ConsumerTerminal(_SubscribeMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.CONSUMER

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribeMixin.__init__(self, _api.pcAsyncReceiveMessage)


class ConsumerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, ConsumerTerminal):
    TerminalClass = ConsumerTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


ProducerTerminal.CounterTerminalType = ConsumerTerminal
ConsumerTerminal.CounterTerminalType = ProducerTerminal
ConsumerTerminal.ProtoTerminalClass = ConsumerProtoTerminal


class CachedProducerTerminal(_PublishMixin, _SubscribableMixin, _Terminal):
    TERMINAL_TYPE = _api.TerminalTypes.CACHED_PRODUCER

    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _PublishMixin.__init__(self, _api.cpcPublish)


class CachedProducerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedProducerTerminal):
    TerminalClass = CachedProducerTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


CachedProducerTerminal.ProtoTerminalClass = CachedProducerProtoTerminal


class CachedConsumerTerminal(_CacheMixin, _SubscribeMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.CACHED_CONSUMER

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribeMixin.__init__(self, _api.cpcAsyncReceiveMessage)
        _CacheMixin.__init__(self, _api.cpcGetCachedMessage)


class CachedConsumerProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedConsumerTerminal):
    TerminalClass = CachedConsumerTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


CachedProducerTerminal.CounterTerminalType = CachedConsumerTerminal
CachedConsumerTerminal.CounterTerminalType = CachedProducerTerminal
CachedConsumerTerminal.ProtoTerminalClass = CachedConsumerProtoTerminal


class MasterTerminal(_PublishMixin, _SubscribeMixin, _SubscribableMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.MASTER

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _SubscribeMixin.__init__(self, _api.msAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.msPublish)


class MasterProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, MasterTerminal):
    TerminalClass = MasterTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


MasterProtoTerminal.ProtoTerminalClass = MasterProtoTerminal


class SlaveTerminal(_PublishMixin, _SubscribeMixin, _SubscribableMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.SLAVE

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _SubscribeMixin.__init__(self, _api.msAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.msPublish)


class SlaveProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, SlaveTerminal):
    TerminalClass = SlaveTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


MasterTerminal.CounterTerminalType = SlaveTerminal
SlaveTerminal.CounterTerminalType = MasterTerminal
SlaveProtoTerminal.ProtoTerminalClass = SlaveProtoTerminal


class CachedMasterTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _SubscribableMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.CACHED_MASTER

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _SubscribeMixin.__init__(self, _api.cmsAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.cmsPublish)
        _CacheMixin.__init__(self, _api.cmsGetCachedMessage)


class CachedMasterProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedMasterTerminal):
    TerminalClass = CachedMasterTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


CachedMasterTerminal.ProtoTerminalClass = CachedMasterProtoTerminal


class CachedSlaveTerminal(_CacheMixin, _PublishMixin, _SubscribeMixin, _SubscribableMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.CACHED_SLAVE

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _SubscribeMixin.__init__(self, _api.cmsAsyncReceiveMessage)
        _PublishMixin.__init__(self, _api.cmsPublish)
        _CacheMixin.__init__(self, _api.cmsGetCachedMessage)


class CachedSlaveProtoTerminal(_MakePublishMessageMixin, _ProtoTerminalMixin, CachedSlaveTerminal):
    TerminalClass = CachedSlaveTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


CachedMasterTerminal.CounterTerminalType = CachedSlaveTerminal
CachedSlaveTerminal.CounterTerminalType = CachedMasterTerminal
CachedSlaveTerminal.ProtoTerminalClass = CachedSlaveProtoTerminal


class ServiceTerminal(_ServiceMixin, _AutoBindTerminal):
    TERMINAL_TYPE = _api.TerminalTypes.SERVICE

    def __init__(self, leaf, name, signature):
        _AutoBindTerminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _ServiceMixin.__init__(self, _api.scAsyncReceiveRequest, _api.scCancelReceiveRequest, _api.scRespondToRequest, _api.scIgnoreRequest)


class ServiceProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ServiceTerminal):
    TerminalClass = ServiceTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


ServiceTerminal.ProtoTerminalClass = ServiceProtoTerminal


class ClientTerminal(_ClientMixin, _SubscribableMixin, _Terminal):
    TERMINAL_TYPE = _api.TerminalTypes.CLIENT

    def __init__(self, leaf, name, signature):
        _Terminal.__init__(self, leaf, self.TERMINAL_TYPE, name, signature)
        _SubscribableMixin.__init__(self)
        _ClientMixin.__init__(self, _api.scAsyncRequest, _api.scCancelRequest)


class ClientProtoTerminal(_MakeRequestResponseMessagesMixin, _ProtoTerminalMixin, ClientTerminal):
    TerminalClass = ClientTerminal

    def __init__(self, leaf, name, proto_module):
        _ProtoTerminalMixin.__init__(self, leaf, name, proto_module)


ServiceTerminal.CounterTerminalType = ClientTerminal
ClientTerminal.CounterTerminalType = ServiceTerminal
ClientTerminal.ProtoTerminalClass = ClientProtoTerminal


_TERMINAL_TYPE_TO_CLASS = [
    DeafMuteTerminal,
    PublishSubscribeTerminal,
    ScatterGatherTerminal,
    CachedPublishSubscribeTerminal,
    ProducerTerminal,
    ConsumerTerminal,
    CachedProducerTerminal,
    CachedConsumerTerminal,
    MasterTerminal,
    SlaveTerminal,
    CachedMasterTerminal,
    CachedSlaveTerminal,
    ServiceTerminal,
    ClientTerminal
]


def terminalTypeToClass(terminalType):
    return _TERMINAL_TYPE_TO_CLASS[terminalType]
