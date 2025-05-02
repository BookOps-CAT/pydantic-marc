import pytest
from pymarc import Indicators, Subfield

from pydantic_marc.marc_rules import RuleSet
from pydantic_marc.validators import validate_field


class TestValidators:
    @pytest.mark.parametrize(
        "tag, data",
        [
            ("001", "foo"),
            ("002", "bar"),
            ("003", "baz"),
            ("005", "foo"),
            ("007", "d|||||"),
            ("007", "a|||||||"),
            ("008", "190306s2017    ht a   j      000 1 hat d"),
            ("009", "bar"),
        ],
    )
    def test_validate_control_field(self, make_mock_info, tag, data):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(data={"rules": rules, "tag": tag}, field_name="data")
        validated_fields = validate_field(data, info=info)
        assert validated_fields == data

    @pytest.mark.parametrize(
        "tag, indicators",
        [
            (
                "010",
                Indicators(
                    " ",
                    " ",
                ),
            ),
            (
                "035",
                Indicators(
                    " ",
                    " ",
                ),
            ),
            (
                "050",
                Indicators(
                    "0",
                    "4",
                ),
            ),
            (
                "245",
                Indicators(
                    "1",
                    "0",
                ),
            ),
        ],
    )
    def test_validate_indicators(self, make_mock_info, indicators, tag):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(
            data={"rules": rules, "tag": tag}, field_name="indicators"
        )
        validated_fields = validate_field(indicators, info=info)
        assert validated_fields == indicators

    @pytest.mark.parametrize(
        "tag, subfields",
        [
            ("010", [Subfield(code="a", value="20251111111111")]),
            ("035", [Subfield(code="a", value="on1234567890")]),
            ("050", [Subfield(code="a", value="F00")]),
            (
                "245",
                [
                    Subfield(code="a", value="Foo: "),
                    Subfield(code="b", value="Bar, "),
                    Subfield(code="c", value="Baz."),
                ],
            ),
        ],
    )
    def test_validate_subfields(self, make_mock_info, subfields, tag):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(data={"rules": rules, "tag": tag}, field_name="subfields")
        validated_fields = validate_field(subfields, info=info)
        assert validated_fields == subfields
