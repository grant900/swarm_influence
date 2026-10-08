from lrucache import LRUCache

def test_get_put():
    c = LRUCache(2); c.put("a", 1); assert c.get("a") == 1
def test_default(): assert LRUCache(1).get("x", 9) == 9
def test_evict():
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.put("c", 3)
    assert c.get("a") is None and len(c) == 2
def test_recency():
    c = LRUCache(2); c.put("a", 1); c.put("b", 2); c.get("a"); c.put("c", 3)
    assert c.get("a") == 1 and c.get("b") is None
def test_update():
    c = LRUCache(2); c.put("a", 1); c.put("a", 5); assert c.get("a") == 5 and len(c) == 1
