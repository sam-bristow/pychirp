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
  package='chirp_00000001',
  syntax='proto3',
  serialized_pb=_b('\n\x0emessages.proto\x12\x0e\x63hirp_00000001\"\x10\n\x0eScatterMessage\"\x1e\n\rGatherMessage\x12\r\n\x05value\x18\x02 \x01(\x08\"\x1f\n\x0ePublishMessage\x12\r\n\x05value\x18\x02 \x01(\x08\x62\x06proto3')
)
_sym_db.RegisterFileDescriptor(DESCRIPTOR)




_SCATTERMESSAGE = _descriptor.Descriptor(
  name='ScatterMessage',
  full_name='chirp_00000001.ScatterMessage',
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


_GATHERMESSAGE = _descriptor.Descriptor(
  name='GatherMessage',
  full_name='chirp_00000001.GatherMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='chirp_00000001.GatherMessage.value', index=0,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
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
  serialized_start=52,
  serialized_end=82,
)


_PUBLISHMESSAGE = _descriptor.Descriptor(
  name='PublishMessage',
  full_name='chirp_00000001.PublishMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='chirp_00000001.PublishMessage.value', index=0,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
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
  serialized_start=84,
  serialized_end=115,
)

DESCRIPTOR.message_types_by_name['ScatterMessage'] = _SCATTERMESSAGE
DESCRIPTOR.message_types_by_name['GatherMessage'] = _GATHERMESSAGE
DESCRIPTOR.message_types_by_name['PublishMessage'] = _PUBLISHMESSAGE

ScatterMessage = _reflection.GeneratedProtocolMessageType('ScatterMessage', (_message.Message,), dict(
  DESCRIPTOR = _SCATTERMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_00000001.ScatterMessage)
  ))
_sym_db.RegisterMessage(ScatterMessage)

GatherMessage = _reflection.GeneratedProtocolMessageType('GatherMessage', (_message.Message,), dict(
  DESCRIPTOR = _GATHERMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_00000001.GatherMessage)
  ))
_sym_db.RegisterMessage(GatherMessage)

PublishMessage = _reflection.GeneratedProtocolMessageType('PublishMessage', (_message.Message,), dict(
  DESCRIPTOR = _PUBLISHMESSAGE,
  __module__ = 'messages_pb2'
  # @@protoc_insertion_point(class_scope:chirp_00000001.PublishMessage)
  ))
_sym_db.RegisterMessage(PublishMessage)


# @@protoc_insertion_point(module_scope)
ScatterMessage.SIGNATURE = 0x00000001
GatherMessage.SIGNATURE = 0x00000001
PublishMessage.SIGNATURE = 0x00000001