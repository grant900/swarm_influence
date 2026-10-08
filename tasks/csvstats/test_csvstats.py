from csvstats import column_means

def test_basic(): assert column_means("a,b\n1,2\n3,4") == {"a": 2.0, "b": 3.0}
def test_blank(): assert column_means("a\n1\n\n3\n") == {"a": 2.0}
def test_missing(): assert column_means("a,b\n1,\n3,4") == {"a": 2.0, "b": 4.0}
def test_quoted(): assert column_means('"x","y"\n1,2\n3,4') == {"x": 2.0, "y": 3.0}
