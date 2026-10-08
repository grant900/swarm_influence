"""Held-out check against a SKU that is not in the visible tests (scored out-of-band). Do not edit."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # the module under test lives one dir up

from prices import get_total


def test_unseen_sku(): assert get_total(["C300"]) == 41.25
def test_mixed(): assert get_total(["A100", "C300"]) == 53.75
