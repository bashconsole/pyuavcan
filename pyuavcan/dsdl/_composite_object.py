#
# Copyright (c) 2019 UAVCAN Development Team
# This software is distributed under the terms of the MIT License.
# Author: Pavel Kirienko <pavel.kirienko@zubax.com>
#

from __future__ import annotations
import abc
import gzip
import numpy
import typing
import pydsdl
import pickle
import base64
import logging
from . import _serialized_representation


_logger = logging.getLogger(__name__)


class CompositeObject(abc.ABC):
    """
    Base class of an instance of a DSDL composite type.
    The entities follow the naming pattern "_.*_" to avoid collisions with DSDL attributes.
    """
    # Type definition as provided by PyDSDL.
    _MODEL_: pydsdl.CompositeType

    # Defined in generated classes.
    _SERIALIZED_REPRESENTATION_BUFFER_SIZE_IN_BYTES_: int

    @abc.abstractmethod
    def _serialize_aligned_(self, _ser_: _serialized_representation.Serializer) -> None:
        """
        Auto-generated serialization method.
        Appends the serialized representation of its object to the supplied Serializer instance.
        The current bit offset of the Serializer instance MUST be byte-aligned.
        This is not a part of the API.
        """
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def _deserialize_aligned_(_des_: _serialized_representation.Deserializer) -> CompositeObject:
        """
        Auto-generated deserialization method. Consumes (some) data from the supplied Deserializer instance.
        Raises a Deserializer.FormatError if the supplied serialized representation is invalid.
        Always returns a valid object unless an exception is raised.
        The current bit offset of the Deserializer instance MUST be byte-aligned.
        This is not a part of the API.
        """
        raise NotImplementedError

    @staticmethod
    def _restore_constant_(encoded_string: str) -> object:
        """Recovers a pickled gzipped constant object from base85 string representation."""
        out = pickle.loads(gzip.decompress(base64.b85decode(encoded_string)))
        assert isinstance(out, object)
        return out

    # These typing hints are provided here for use in the generated classes. They are obviously not part of the API.
    _SerializerTypeVar_ = typing.TypeVar('_SerializerTypeVar_', bound=_serialized_representation.Serializer)
    _DeserializerTypeVar_ = typing.TypeVar('_DeserializerTypeVar_', bound=_serialized_representation.Deserializer)


CompositeObjectTypeVar = typing.TypeVar('CompositeObjectTypeVar', bound=CompositeObject)


# noinspection PyProtectedMember
def serialize(obj: CompositeObject) -> typing.Iterable[memoryview]:
    """
    Constructs a serialized representation of the provided top-level object.
    The resulting serialized representation is padded to one byte in accordance with the Specification.
    The constructed serialized representation is returned as a sequence of byte-aligned fragments which must be
    concatenated in order to obtain the final representation. The objective of this model is to avoid copying data
    into a temporary buffer when possible. Each yielded fragment is of type memoryview pointing to raw unsigned bytes.
    It is guaranteed that at least one fragment is always returned (which may be empty).
    """
    # TODO: update the Serializer class to emit an iterable of fragments.
    ser = _serialized_representation.Serializer.new(obj._SERIALIZED_REPRESENTATION_BUFFER_SIZE_IN_BYTES_)
    obj._serialize_aligned_(ser)
    yield ser.buffer.data


# noinspection PyProtectedMember
def try_deserialize(cls: typing.Type[CompositeObjectTypeVar],
                    fragmented_serialized_representation: typing.Iterable[memoryview]) \
        -> typing.Optional[CompositeObjectTypeVar]:
    """
    Constructs a Python object representing an instance of the supplied data type from its serialized representation.
    Returns None if the provided serialized representation is invalid.
    This function will never raise an exception for invalid input data; the only possible outcome of an invalid data
    being supplied is None at the output. A raised exception can only indicate an error in the deserialization logic.

    SAFETY WARNING: THE CONSTRUCTED OBJECT MAY CONTAIN ARRAYS REFERENCING THE MEMORY ALLOCATED FOR THE SERIALIZED
                    REPRESENTATION. THEREFORE, IN ORDER TO AVOID UNINTENDED DATA CORRUPTION, THE CALLER MUST DESTROY
                    ALL REFERENCES TO THE SERIALIZED REPRESENTATION IMMEDIATELY AFTER THE INVOCATION.

    USAGE WARNING: The supplied fragments of the serialized representation should be writeable. If they are not,
                   some of the array-typed fields of the constructed object may be read-only.
    """
    # TODO: update the Deserializer class to support fragmented input.
    # join() on one element will create a copy, so that is very expensive.
    fragments = list(fragmented_serialized_representation)
    contiguous = fragments[0] if len(fragments) == 1 else bytearray().join(fragmented_serialized_representation)
    deserializer = _serialized_representation.Deserializer.new(contiguous)
    try:
        return cls._deserialize_aligned_(deserializer)  # type: ignore
    except _serialized_representation.Deserializer.FormatError:
        # Use explicit level check to avoid unnecessary load in production.
        # This is necessary because we perform complex data transformations before invoking the logger.
        if _logger.isEnabledFor(logging.INFO):
            _logger.info('Invalid serialized representation of %s: %s', get_model(cls), deserializer, exc_info=True)
        return None


def get_model(class_or_instance: typing.Union[typing.Type[CompositeObject], CompositeObject]) -> pydsdl.CompositeType:
    # noinspection PyProtectedMember
    out = class_or_instance._MODEL_
    assert isinstance(out, pydsdl.CompositeType)
    return out
