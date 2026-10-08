"""Held-out decode check on a second capture (scored out-of-band). Do not edit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the decoder under test lives one dir up

from records import decode_records

EXPECTED = [
 {
  "type": "sample",
  "ts": "2026-09-01T01:07:00Z",
  "value": 196.075,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   90.7,
   62.43
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T02:01:00Z",
  "value": 3839.195,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T02:58:00Z",
  "value": 1863.851,
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T03:54:00Z",
  "value": 601.482,
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T04:18:00Z",
  "value": 988.78,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   1.7,
   85.3,
   33.3,
   22.43,
   92.66,
   37.02
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T04:32:00Z",
  "value": 1055.704,
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T04:49:00Z",
  "value": 2063.919,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   58.66
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T05:40:00Z",
  "value": 99.72,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T06:25:00Z",
  "value": 1489.243,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   75.02,
   23.2,
   4.2,
   38.29,
   20.33,
   20.27
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T07:04:00Z",
  "value": 94.471,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T07:40:00Z",
  "value": 3683.678,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T08:17:00Z",
  "value": 2212.93,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T09:38:00Z",
  "value": 2176.495,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T11:00:00Z",
  "value": 2283.636,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   12.1,
   9.63
  ],
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T11:43:00Z",
  "value": 2962.577,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T12:47:00Z",
  "value": 2894.719,
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T14:00:00Z",
  "value": 2324.482,
  "flags": [
   "stale"
  ]
 },
 {
  "type": "batch",
  "values": [
   50.32,
   53.69
  ],
  "flags": [
   "low_battery"
  ]
 },
 {
  "type": "sample",
  "ts": "2026-09-01T15:00:00Z",
  "value": 1536.316,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T15:07:00Z",
  "value": 696.09,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   96.61,
   8.03,
   67.14,
   33.63,
   47.09,
   41.11
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T15:48:00Z",
  "value": 1123.257,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T16:50:00Z",
  "value": 1460.689,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   74.2,
   86.96
  ],
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T18:11:00Z",
  "value": 2434.148,
  "flags": []
 },
 {
  "type": "sample",
  "ts": "2026-09-01T19:19:00Z",
  "value": 1571.615,
  "flags": []
 },
 {
  "type": "batch",
  "values": [
   87.24,
   63.88,
   43.01,
   77.51,
   87.17,
   50.42
  ],
  "flags": []
 }
]


def test_hidden_capture():
    import pathlib
    data = (pathlib.Path(__file__).parent / "records_hidden.bin").read_bytes()
    assert decode_records(data) == EXPECTED
