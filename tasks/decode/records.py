"""Decoder for the internal `trk` telemetry record format (undocumented).

`records.bin` is a capture of the device feed; `decode_records` turns it into a list of
record dicts (shape pinned by test_records.py). The format was never documented, so this
module is our best-effort reader.
"""


def decode_records(data: bytes) -> list[dict]:
    raise NotImplementedError
