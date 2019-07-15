#
# Copyright (c) 2019 UAVCAN Development Team
# This software is distributed under the terms of the MIT License.
# Author: Pavel Kirienko <pavel.kirienko@zubax.com>
#

"""
The util package contains various entities that are commonly useful in PyUAVCAN-based applications.
"""

# noinspection PyShadowingBuiltins
from . import hash as hash

from ._refragment import refragment as refragment

from ._mark_last import mark_last as mark_last

from ._repr import repr_attributes as repr_attributes
from ._repr import repr_attributes_noexcept as repr_attributes_noexcept

from ._introspect import iter_descendants as iter_descendants
from ._introspect import import_submodules as import_submodules