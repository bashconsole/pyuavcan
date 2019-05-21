#
# Copyright (c) 2019 UAVCAN Development Team
# This software is distributed under the terms of the MIT License.
# Author: Pavel Kirienko <pavel.kirienko@zubax.com>
#

from __future__ import annotations
import enum
import typing
import dataclasses
import pyuavcan.transport


@dataclasses.dataclass(frozen=True)
class Frame:
    class Format(enum.IntEnum):
        STANDARD = 11
        EXTENDED = 29

    identifier: int
    data:       bytearray
    format:     Format
    loopback:   bool        # Indicates a loopback request for outgoing frames; marks loopback for received frames.

    def __post_init__(self) -> None:
        if not isinstance(self.format, self.Format):
            raise ValueError(f'Invalid frame format: {self.format}')

        if not (0 <= self.identifier < 2 ** int(self.format)):
            raise ValueError(f'Invalid CAN ID for format {self.format}: {self.identifier}')

        if len(self.data) not in _LENGTH_TO_DLC:
            raise ValueError(f'Unsupported data length: {len(self.data)}')

    @property
    def data_length_code(self) -> int:
        try:
            return _LENGTH_TO_DLC[len(self.data)]
        except LookupError:
            raise ValueError(f'{len(self.data)} bytes is not a valid data length; '
                             f'valid length values are: {list(_LENGTH_TO_DLC.keys())}') from None

    @staticmethod
    def convert_data_length_code_to_length(dlc: int) -> int:
        try:
            return _DLC_TO_LENGTH[dlc]
        except LookupError:
            raise ValueError(f'{dlc} is not a valid DLC') from None

    def __str__(self) -> str:
        ide = {
            self.Format.EXTENDED: '0x%08x',
            self.Format.STANDARD: '0x%03x',
        }[self.format] % self.identifier
        data_hex = ' '.join(map('{:02x}'.format, self.data))
        data_ascii = ''.join((chr(x) if 32 <= x <= 126 else '.') for x in self.data)
        out = f"{ide}  {data_hex}  '{data_ascii}'{'  loopback' if self.loopback else ''}"
        return out


@dataclasses.dataclass(frozen=True)
class TimestampedFrame(Frame):
    timestamp: pyuavcan.transport.Timestamp

    def __str__(self) -> str:
        return f'{self.timestamp}: {super(TimestampedFrame, self).__str__()}'


_DLC_TO_LENGTH = [0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64]
_LENGTH_TO_DLC: typing.Dict[int, int] = dict(zip(*list(zip(*enumerate(_DLC_TO_LENGTH)))[::-1]))  # type: ignore
assert len(_LENGTH_TO_DLC) == 16 == len(_DLC_TO_LENGTH)
for item in _DLC_TO_LENGTH:
    assert _DLC_TO_LENGTH[_LENGTH_TO_DLC[item]] == item, 'Invalid DLC tables'


def _unittest_can_media_frame() -> None:
    assert str(Frame(0, bytearray(), Frame.Format.STANDARD, False)) == "0x000    ''"

    assert str(Frame(0x12345678, bytearray(b'Hello\x01\x02\x7F'), Frame.Format.EXTENDED, True)) == \
        "0x12345678  48 65 6c 6c 6f 01 02 7f  'Hello...'  loopback"

    assert str(TimestampedFrame(0x12345678,
                                bytearray(b'Hello\x01\x02\x7F'),
                                Frame.Format.EXTENDED,
                                True,
                                pyuavcan.transport.Timestamp(wall_ns=1558481132502003000,
                                                             monotonic_ns=635720258263416))) == \
        "2019-05-22T02:25:32.502003/635720.258263416: 0x12345678  48 65 6c 6c 6f 01 02 7f  'Hello...'  loopback"