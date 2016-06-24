# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: messages.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='messages.proto',
  package='chirp_000009cd',
  syntax='proto3',
  serialized_pb=_b('\n\x0emessages.proto\x12\x0e\x63hirp_000009cd\"\x10\n\x0eScatterMessage\"|\n\rGatherMessage\x12\x11\n\ttimestamp\x18\x01 \x01(\x04\x12\x31\n\x05value\x18\x02 \x01(\x0b\x32\".chirp_000009cd.GatherMessage.Pair\x1a%\n\x04Pair\x12\r\n\x05\x66irst\x18\x01 \x01(\t\x12\x0e\n\x06second\x18\x02 \x01(\t\"~\n\x0ePublishMessage\x12\x11\n\ttimestamp\x18\x01 \x01(\x04\x12\x32\n\x05value\x18\x02 \x01(\x0b\x32#.chirp_000009cd.PublishMessage.Pair\x1a%\n\x04Pair\x12\r\n\x05\x66irst\x18\x01 \x01(\t\x12\x0e\n\x06second\x18\x02 \x01(\tb\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_SCATTERMESSAGE = _descriptor.Descriptor(
  name='ScatterMessage',
  full_name='chirp_000009cd.ScatterMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=34,
  serialized_end=50,
)


_GATHERMESSAGE_PAIR = _descriptor.Descriptor(
  name='Pair',
  full_name='chirp_000009cd.GatherMessage.Pair',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='first', full_name='chirp_000009cd.GatherMessage.Pair.first', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='second', full_name='chirp_000009cd.GatherMessage.Pair.second', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=139,
  serialized_end=176,
)

_GATHERMESSAGE = _descriptor.Descriptor(
  name='GatherMessage',
  full_name='chirp_000009cd.GatherMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='chirp_000009cd.GatherMessage.timestamp', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='chirp_000009cd.GatherMessage.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_GATHERMESSAGE_PAIR, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=52,
  serialized_end=176,
)


_PUBLISHMESSAGE_PAIR = _descriptor.Descriptor(
  name='Pair',
  full_name='chirp_000009cd.PublishMessage.Pair',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='first', full_name='chirp_000009cd.PublishMessage.Pair.first', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='second', full_name='chirp_000009cd.PublishMessage.Pair.second', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=139,
  serialized_end=176,
)

_PUBLISHMESSAGE = _descriptor.Descriptor(
  name='PublishMessage',
  full_name='chirp_000009cd.PublishMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='timestamp', full_name='chirp_000009cd.PublishMessage.timestamp', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    _descriptor.FieldDescriptor(
      name='value', full_name='chirp_000009cd.PublishMessage.value', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[_PUBLISHMESSAGE_PAIR, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=178,
  serialized_end=304,
)

_GATHERMESSAGE_PAIR.containing_type = _GATHERMESSAGE
_GATHERMESSAGE.fields_by_name['value'].message_type = _GATHERMESSAGE_PAIR
_PUBLISHMESSAGE_PAIR.containing_type = _PUBLISHMESSAGE
_PUBLISHMESSAGE.fields_by_name['value'].message_type = _PUBLISHMESSAGE_PAIR
DESCRIPTOR.message_types_by_name['ScatterMessage'] = _SCATTERMESSAGE
DESCRIPTOR.message_types_by_name['GatherMessage'] = _GATHERMESSAGE
DESCRIPTOR.message_types_by_name['PublishMessage'] = _PUBLISHMESSAGE

ScatterMessage = _reflection.GeneratedProtocolMessageType('ScatterMessage', (_message.Message,), dict(
  DESCRIPTOR = _SCATTERMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_000009cd.ScatterMessage)
  ))
_sym_db.RegisterMessage(ScatterMessage)

GatherMessage = _reflection.GeneratedProtocolMessageType('GatherMessage', (_message.Message,), dict(

  Pair = _reflection.GeneratedProtocolMessageType('Pair', (_message.Message,), dict(
    DESCRIPTOR = _GATHERMESSAGE_PAIR,
    __module__ = 'messages_pb2'
    # @@protoc_insertion_point(class_scope:chirp_000009cd.GatherMessage.Pair)
    ))
  ,
  DESCRIPTOR = _GATHERMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_000009cd.GatherMessage)
  ))
_sym_db.RegisterMessage(GatherMessage)
_sym_db.RegisterMessage(GatherMessage.Pair)

PublishMessage = _reflection.GeneratedProtocolMessageType('PublishMessage', (_message.Message,), dict(

  Pair = _reflection.GeneratedProtocolMessageType('Pair', (_message.Message,), dict(
    DESCRIPTOR = _PUBLISHMESSAGE_PAIR,
    __module__ = 'messages_pb2'
    # @@protoc_insertion_point(class_scope:chirp_000009cd.PublishMessage.Pair)
    ))
  ,
  DESCRIPTOR = _PUBLISHMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_000009cd.PublishMessage)
  ))
_sym_db.RegisterMessage(PublishMessage)
_sym_db.RegisterMessage(PublishMessage.Pair)


# @@protoc_insertion_point(module_scope)
ScatterMessage.SIGNATURE = 0x000009cd
GatherMessage.SIGNATURE = 0x000009cd
PublishMessage.SIGNATURE = 0x000009cd
