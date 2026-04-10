from pydantic_marc import __title__, __version__


def test_version():
    assert __version__ == "0.2.0"


def test_title():
    assert __title__ == "pydantic-marc"
