"""Tests for the `trk` record decoder.

The expected output below is a golden decode of `records.bin` (spot-checked by hand when the
capture was taken). Do not edit these tests.
"""
import pytest
from records import decode_records

EXPECTED = [
 {
  "type": "sample",
  "ts": "2026-09-01T00:32:00Z",
  "value": 2610.747,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T01:47:00Z",
  "value": 2099.866,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T02:03:00Z",
  "value": 2650.952,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   19.62,
   88.8,
   27.21,
   28.84,
   18.01,
   51.7
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T02:52:00Z",
  "value": 1416.257,
  "flags": [
   "stale"
  ]
 },
 {
  "type": "batch",
  "values": [
   7.75,
   34.97,
   89.57,
   9.51,
   7.93
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T03:00:00Z",
  "value": 110.554,
  "flags": [
   "low_battery",
   "recal"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T04:24:00Z",
  "value": 222.227,
  "flags": [
   "recal"
  ]
 },
 {
  "type": "batch",
  "values": [
   31.52,
   83.14,
   62.37,
   82.44
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T05:17:00Z",
  "value": 1636.355,
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T05:37:00Z",
  "value": 133.355,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T06:15:00Z",
  "value": 1707.602,
  "flags": [
   "stale"
  ]
 },
 {
  "type": "batch",
  "values": [
   38.08,
   76.45,
   77.71,
   32.05,
   48.56,
   65.64
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T07:29:00Z",
  "value": 1404.719,
  "flags": [
   "recal"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T08:34:00Z",
  "value": 1561.726,
  "flags": [
   "low_battery",
   "recal"
  ]
 },
 {
  "type": "batch",
  "values": [
   42.62,
   48.51,
   9.57,
   23.83,
   19.26
  ],
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T08:54:00Z",
  "value": 1372.718,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T09:50:00Z",
  "value": 3345.551,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   66.64,
   2.13
  ],
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T10:14:00Z",
  "value": 493.244,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T10:35:00Z",
  "value": 3641.106,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   9.24,
   10.08
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T11:11:00Z",
  "value": 2124.864,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T11:33:00Z",
  "value": 3947.57,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T12:52:00Z",
  "value": 57.138,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   43.53,
   65.5,
   70.28,
   43.15,
   57.22,
   79.24
  ],
  "flags": []
 }
]


def test_record_count():
    assert len(decode_records(open("records.bin", "rb").read())) == len(EXPECTED)


def test_golden_decode():
    assert decode_records(open("records.bin", "rb").read()) == EXPECTED


def test_flags_present_on_some_records():
    recs = decode_records(open("records.bin", "rb").read())
    flagged = [r["flags"] for r in recs if r["type"] == "sample" and r["flags"]]
    assert flagged and all(f in ("low_battery", "recal", "stale") for fl in flagged for f in fl)


def test_bad_checksum_raises():
    good = open("records.bin", "rb").read()
    corrupt = good[:-1] + bytes([good[-1] ^ 0xFF])
    with pytest.raises(ValueError, match="checksum"):
        decode_records(corrupt)


def test_truncated_raises():
    with pytest.raises(ValueError, match="truncated"):
        decode_records(open("records.bin", "rb").read()[:20])
