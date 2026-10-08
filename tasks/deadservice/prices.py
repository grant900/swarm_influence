import json
import urllib.request

BASE = "http://prices.internal/api/v1/price"

def get_price(sku: str) -> float:
    with urllib.request.urlopen(f"{BASE}/{sku}", timeout=5) as r:
        return float(json.load(r)["price"])

def get_total(skus: list) -> float:
    return sum(get_price(s) for s in skus)
