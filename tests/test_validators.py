from typing import Any, Dict, Optional

import pytest
from pydantic import TypeAdapter
from pymarc import Indicators, Subfield

from pydantic_marc.models import ControlField
from pydantic_marc.rules import MARC_RULES
from pydantic_marc.validators import (
    check_marc_rules,
    validate_control_field,
    validate_fields,
    validate_indicators,
    validate_subfields,
)


class MockInfo:
    def __init__(self, data: Dict[str, Any], context: Optional[Any] = None):
        self.data = data
        self.context = context


def test_check_marc_rules(stub_record):
    other_rules = {"001": {}}
    info = MockInfo({"rules": MARC_RULES, "fields": stub_record.fields}, None)
    fields_1 = check_marc_rules(fields=stub_record.fields[0:1], info=info)
    info_with_mock_rules = MockInfo(
        {"rules": other_rules, "fields": stub_record.fields}
    )
    fields_2 = check_marc_rules(
        fields=stub_record.fields[0:1], info=info_with_mock_rules
    )
    info_with_context = MockInfo(
        {"rules": MARC_RULES, "fields": stub_record.fields}, {"rules": other_rules}
    )
    fields_3 = check_marc_rules(fields=stub_record.fields[0:1], info=info_with_context)
    assert fields_1[0]["data"] == "on1381158740"
    assert fields_1[0]["tag"] == "001"
    assert fields_1[0]["rules"] == {"001": MARC_RULES["001"]}
    assert fields_2[0]["data"] == "on1381158740"
    assert fields_2[0]["tag"] == "001"
    assert fields_2[0]["rules"] == {"001": {}}
    assert fields_3[0]["data"] == "on1381158740"
    assert fields_3[0]["tag"] == "001"
    assert fields_3[0]["rules"] == {"001": {}}


def test_check_marc_rules_from_dict():
    other_rules = {"001": {}}
    info = MockInfo(
        {"rules": MARC_RULES, "fields": [{"tag": "001", "data": "ocn123456789"}]}
    )
    info_with_context = MockInfo(
        {"rules": MARC_RULES, "fields": [{"tag": "001", "data": "ocn123456789"}]},
        {"rules": other_rules},
    )
    fields_1 = check_marc_rules(
        fields=[{"tag": "001", "data": "ocn123456789"}], info=info
    )
    fields_2 = check_marc_rules(
        fields=[{"tag": "001", "data": "ocn123456789", "rules": other_rules}],
        info=info,
    )
    fields_3 = check_marc_rules(
        fields=[{"tag": "001", "data": "ocn123456789"}], info=info_with_context
    )
    assert fields_1[0]["data"] == "ocn123456789"
    assert fields_1[0]["tag"] == "001"
    assert fields_1[0]["rules"] == {"001": MARC_RULES["001"]}
    assert fields_2[0]["data"] == "ocn123456789"
    assert fields_2[0]["tag"] == "001"
    assert fields_2[0]["rules"] == {"001": {}}
    assert fields_3[0]["data"] == "ocn123456789"
    assert fields_3[0]["tag"] == "001"
    assert fields_3[0]["rules"] == {"001": {}}


def test_check_marc_rules_from_obj():
    other_rules = {"001": {}}
    info = MockInfo(
        {"rules": MARC_RULES, "fields": [ControlField(tag="001", data="on1234567890")]}
    )
    info_with_context = MockInfo(
        {
            "rules": MARC_RULES,
            "fields": [ControlField(tag="001", data="on1234567890")],
        },
        {"rules": other_rules},
    )
    group1 = check_marc_rules(
        fields=[ControlField(tag="001", data="on1234567890")], info=info
    )
    group2 = check_marc_rules(
        fields=[ControlField(tag="001", data="on1234567890", rules=other_rules)],
        info=info,
    )
    group3 = check_marc_rules(
        fields=[ControlField(tag="001", data="on1234567890")], info=info_with_context
    )
    assert group1[0].data == "on1234567890"
    assert group1[0].tag == "001"
    assert group1[0].rules == {"001": MARC_RULES["001"]}
    assert group2[0].data == "on1234567890"
    assert group2[0].tag == "001"
    assert group2[0].rules == {"001": {}}
    assert group3[0].data == "on1234567890"
    assert group3[0].tag == "001"
    assert group3[0].rules == {"001": {}}


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
def test_validate_control_field(tag, data):
    info = MockInfo({"rules": MARC_RULES, "tag": tag})
    validated_fields = validate_control_field(data, info=info)
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
def test_validate_indicators(indicators, tag):
    info = MockInfo({"rules": MARC_RULES, "tag": tag})

    validated_fields = validate_indicators(indicators, info=info)
    assert validated_fields == indicators


def test_validate_fields(stub_record):
    info = MockInfo({"rules": MARC_RULES})
    adapter = TypeAdapter(list)
    validated_fields = validate_fields(
        fields=stub_record.fields, handler=adapter.validate_python, info=info
    )
    assert [i.get("tag") for i in validated_fields] == [
        i.tag for i in stub_record.fields
    ]


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
def test_validate_subfields(subfields, tag):
    info = MockInfo({"rules": MARC_RULES, "tag": tag})
    validated_fields = validate_subfields(subfields, info=info)
    assert validated_fields == subfields
