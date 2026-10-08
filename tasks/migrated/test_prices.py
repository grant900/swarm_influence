from prices import get_total

def test_single(): assert get_total(["A100"]) == 12.5
def test_pair(): assert get_total(["A100", "B200"]) == 30.0
def test_empty(): assert get_total([]) == 0
