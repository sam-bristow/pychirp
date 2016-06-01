# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: chirp-49164.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import descriptor_pb2 as google_dot_protobuf_dot_descriptor__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='chirp-49164.proto',
  package='',
  syntax='proto3',
  serialized_pb=_b('\n\x11\x63hirp-49164.proto\x1a google/protobuf/descriptor.proto\"\x1f\n\x0eScatterMessage\x12\r\n\x05value\x18\x02 \x01(\x01\"\x1e\n\rGatherMessage\x12\r\n\x05value\x18\x02 \x01(\x01\"\x1f\n\x0ePublishMessage\x12\r\n\x05value\x18\x02 \x01(\x01:1\n\tsignature\x12\x1c.google.protobuf.FileOptions\x18\xd0\x86\x03 \x01(\rB\x06\x80\xb5\x18\x8c\x80\x03\x62\x06proto3')
  ,
  dependencies=[google_dot_protobuf_dot_descriptor__pb2.DESCRIPTOR,])
_sym_db.RegisterFileDescriptor(DESCRIPTOR)


SIGNATURE_FIELD_NUMBER = 50000
signature = _descriptor.FieldDescriptor(
  name='signature', full_name='signature', index=0,
  number=50000, type=13, cpp_type=3, label=1,
  has_default_value=False, default_value=0,
  message_type=None, enum_type=None, containing_type=None,
  is_extension=True, extension_scope=None,
  options=None)


_SCATTERMESSAGE = _descriptor.Descriptor(
  name='ScatterMessage',
  full_name='ScatterMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='ScatterMessage.value', index=0,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=55,
  serialized_end=86,
)


_GATHERMESSAGE = _descriptor.Descriptor(
  name='GatherMessage',
  full_name='GatherMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='GatherMessage.value', index=0,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=88,
  serialized_end=118,
)


_PUBLISHMESSAGE = _descriptor.Descriptor(
  name='PublishMessage',
  full_name='PublishMessage',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='PublishMessage.value', index=0,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=0,
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
  serialized_start=120,
  serialized_end=151,
)

DESCRIPTOR.message_types_by_name['ScatterMessage'] = _SCATTERMESSAGE
DESCRIPTOR.message_types_by_name['GatherMessage'] = _GATHERMESSAGE
DESCRIPTOR.message_types_by_name['PublishMessage'] = _PUBLISHMESSAGE
DESCRIPTOR.extensions_by_name['signature'] = signature

ScatterMessage = _reflection.GeneratedProtocolMessageType('ScatterMessage', (_message.Message,), dict(
  DESCRIPTOR = _SCATTERMESSAGE,
  __module__ = 'chirp_49164_pb2'
  # @@protoc_insertion_point(class_scope:ScatterMessage)
  ))
_sym_db.RegisterMessage(ScatterMessage)

GatherMessage = _reflection.GeneratedProtocolMessageType('GatherMessage', (_message.Message,), dict(
  DESCRIPTOR = _GATHERMESSAGE,
  __module__ = 'chirp_49164_pb2'
  # @@protoc_insertion_point(class_scope:GatherMessage)
  ))
_sym_db.RegisterMessage(GatherMessage)

PublishMessage = _reflection.GeneratedProtocolMessageType('PublishMessage', (_message.Message,), dict(
  DESCRIPTOR = _PUBLISHMESSAGE,
  __module__ = 'chirp_49164_pb2'
  # @@protoc_insertion_point(class_scope:PublishMessage)
  ))
_sym_db.RegisterMessage(PublishMessage)

google_dot_protobuf_dot_descriptor__pb2.FileOptions.RegisterExtension(signature)

DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('\200\265\030\214\200\003'))
# @@protoc_insertion_point(module_scope)
