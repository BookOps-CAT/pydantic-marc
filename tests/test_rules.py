import pytest

from pydantic_marc.rules import MARC_RULES


@pytest.mark.parametrize(
    "tag, rule",
    [
        ("001", {"repeatable": False, "length": None, "required": False}),
        ("003", {"repeatable": False, "length": None, "required": False}),
        ("005", {"repeatable": False, "length": None, "required": False}),
        ("006", {"repeatable": True, "length": 18, "required": False}),
        (
            "007",
            {
                "repeatable": True,
                "length": {
                    "a": 8,
                    "c": [6, 14],
                    "d": 6,
                    "f": 10,
                    "g": 9,
                    "h": 13,
                    "k": 6,
                    "m": 23,
                    "o": 2,
                    "q": 2,
                    "r": 11,
                    "s": 14,
                    "t": 2,
                    "v": 9,
                    "z": 2,
                },
                "required": False,
            },
        ),
        ("008", {"repeatable": False, "length": 40, "required": True}),
    ],
)
def test_marc_rules_control_fields(tag, rule):
    rule.update({"ind1": None, "ind2": None, "subfields": None})
    assert MARC_RULES.get(tag) == rule


def test_marc_rules_data_fields_020():
    assert MARC_RULES.get("020") == {
        "repeatable": True,
        "ind1": ["", " "],
        "ind2": ["", " "],
        "subfields": {
            "valid": ["a", "c", "q", "z", "6", "8"],
            "repeatable": ["q", "z", "8"],
            "non_repeatable": ["a", "c", "6"],
        },
        "length": None,
        "required": False,
    }


def test_marc_rules_data_fields_900():
    assert MARC_RULES.get("900") is None


def test_marc_rules_data_fields_count():
    assert len(list(MARC_RULES.keys())) == 241
