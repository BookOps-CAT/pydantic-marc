import pytest

from pydantic_marc.marc_rules import Rule, RuleSet


def test_rule_set():
    rules = RuleSet()
    assert rules.rules["001"].tag == "001"
    assert rules.rules["001"].repeatable is False
    assert rules.rules["001"].required is False


@pytest.mark.parametrize(
    "tag, repeatable, length, required",
    [
        ("001", False, None, False),
        ("003", False, None, False),
        ("005", False, None, False),
        ("006", True, 18, False),
        (
            "007",
            True,
            {
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
            False,
        ),
        ("008", False, 40, True),
    ],
)
def test_marc_rules_control_fields(tag, repeatable, length, required):
    rules = RuleSet()
    rule = Rule(
        tag=tag,
        repeatable=repeatable,
        length=length,
        required=required,
        ind1=None,
        ind2=None,
        subfields=None,
    )
    assert rules.rules.get(tag) == rule


def test_marc_rules_data_fields_020():
    rules = RuleSet()
    assert rules.rules.get("020") == Rule(
        tag="020",
        repeatable=True,
        ind1=["", " "],
        ind2=["", " "],
        subfields={
            "valid": ["a", "c", "q", "z", "6", "8"],
            "repeatable": ["q", "z", "8"],
            "non_repeatable": ["a", "c", "6"],
        },
        length=None,
        required=False,
    )
    assert rules.rules.get("020") == Rule.create_default("020")


def test_marc_rules_data_fields_900():
    rules = RuleSet()
    assert rules.rules.get("900") is None
    assert Rule.create_default("900") is None


def test_marc_rules_data_fields_count():
    rules = RuleSet()
    assert len(rules.rules.keys()) == 241
