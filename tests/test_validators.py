import pytest
from pydantic import ValidationError
from pymarc import Indicators, Subfield

from pydantic_marc.marc_rules import RuleSet
from pydantic_marc.validators import validate_field, validate_leader, validate_marc_data


class TestFieldValidators:
    @pytest.mark.parametrize(
        "tag, data",
        [
            ("001", "foo"),
            ("002", "bar"),
            ("003", "baz"),
            ("005", "20250101000001.0"),
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
        "tag, data",
        [
            ("007", "d|"),
            ("007", "a"),
            ("008", "190306s2017    ht a   j"),
        ],
    )
    def test_validate_control_field_invalid(self, make_mock_info, tag, data):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(data={"rules": rules, "tag": tag}, field_name="data")
        with pytest.raises(ValidationError) as e:
            validate_field(data, info=info)
        assert len(e.value.errors()) == 1
        assert e.value.errors()[0]["type"] == "control_field_length_invalid"
        assert tag in e.value.errors()[0]["loc"]

    @pytest.mark.parametrize(
        "tag, indicators",
        [
            ("010", Indicators(" ", " ")),
            ("035", Indicators(" ", " ")),
            ("050", Indicators("0", "4")),
            ("245", Indicators("1", "0")),
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
        "tag, indicators",
        [
            ("010", Indicators("0", "0")),
            ("035", Indicators("0", "0")),
            ("050", Indicators("9", "9")),
            ("245", Indicators(" ", " ")),
        ],
    )
    def test_validate_indicators_invalid(self, make_mock_info, indicators, tag):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(
            data={"rules": rules, "tag": tag}, field_name="indicators"
        )
        with pytest.raises(ValidationError) as e:
            validate_field(indicators, info=info)
        assert len(e.value.errors()) == 2
        assert e.value.errors()[0]["type"] == "invalid_indicator"
        assert e.value.errors()[1]["type"] == "invalid_indicator"

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

    @pytest.mark.parametrize(
        "tag, subfields",
        [
            ("010", [Subfield(code="q", value="20251111111111")]),
            ("035", [Subfield(code="r", value="on1234567890")]),
            ("050", [Subfield(code="s", value="F00")]),
            (
                "245",
                [Subfield(code="t", value="Foo: ")],
            ),
        ],
    )
    def test_validate_subfields_invalid(self, make_mock_info, subfields, tag):
        rules = RuleSet().rules.get(tag, None)
        info = make_mock_info(data={"rules": rules, "tag": tag}, field_name="subfields")
        with pytest.raises(ValidationError) as e:
            validate_field(subfields, info=info)
        assert len(e.value.errors()) == 1
        assert e.value.errors()[0]["type"] == "subfield_not_allowed"
        assert tag in e.value.errors()[0]["loc"]


class TestMarcRecordValidators:
    def test_validate_marc_data(self, make_mock_info):
        field_list = [
            {"tag": "001", "data": "on1381158740"},
            {"tag": "008", "data": "190306s2017    ht a   j      000 1 hat d"},
            {
                "tag": "245",
                "indicators": Indicators("0", "0"),
                "subfields": [Subfield(code="a", value="Title :")],
            },
        ]
        rules = RuleSet()
        info = make_mock_info(data={"rules": rules}, field_name="fields")
        validated_fields = validate_marc_data(data=field_list, info=info)
        assert validated_fields == field_list

    def test_validate_marc_data_invalid(self, make_mock_info):
        field_list = [
            {"tag": "001", "data": "on1381158740"},
            {"tag": "008", "data": "190306s2017    ht a   j      000 1 hat d"},
        ]
        info = make_mock_info(data={"rules": RuleSet()}, field_name="fields")
        with pytest.raises(ValidationError) as e:
            validate_marc_data(data=field_list, info=info)
        assert len(e.value.errors()) == 1
        assert e.value.errors()[0]["type"] == "missing_required_field"
        assert "245" in e.value.errors()[0]["loc"]

    @pytest.mark.parametrize(
        "leader", ["00454cam a22001575i 4500", "00454nam a2200157 i 4500"]
    )
    def test_validate_leader(self, leader, make_mock_info):
        leader_output = validate_leader(
            leader,
            info=make_mock_info(
                data={"rules": RuleSet(), "tag": "LDR"}, field_name="leader"
            ),
        )
        assert leader_output == leader
