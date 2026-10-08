from slugify import slugify

def test_basic(): assert slugify("Hello World") == "hello-world"
def test_punct(): assert slugify("Hello, World!") == "hello-world"
def test_collapse(): assert slugify("a   b---c") == "a-b-c"
def test_edges(): assert slugify("  --Hi--  ") == "hi"
def test_empty(): assert slugify("!!!") == ""
