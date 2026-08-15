from superterm.tools.preview import detect_python_markers, detect_python_version

PY2_SNIPPET = """
print "hello world"
try:
    pass
except Exception, e:
    print e
for i in xrange(10):
    pass
"""

PY3_SNIPPET = """
def greet(name: str) -> str:
    print(f"hello {name}")
    return name
"""


def test_detects_python2():
    assert detect_python_version(PY2_SNIPPET) == "python2"
    markers = detect_python_markers(PY2_SNIPPET)
    assert "print statement (no parentheses)" in markers
    assert "xrange()" in markers


def test_detects_python3():
    assert detect_python_version(PY3_SNIPPET) == "python3"
    assert detect_python_markers(PY3_SNIPPET) == []
