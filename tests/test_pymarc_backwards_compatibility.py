from typing import Optional

import pytest
from pydantic import ValidationError
from pymarc import Field as PymarcField
from pymarc import MARCReader
from pymarc import Record as PymarcRecord
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.fields import (
    ControlField,
    DataField,
    PydanticIndicators,
    PydanticSubfield,
)
from pydantic_marc.marc_rules import Rule, RuleSet
from pydantic_marc.models import MarcRecord


@pytest.fixture
def get_default_rule():
    rules = RuleSet()

    def _get_default_rule(tag: str, subtype: Optional[str] = None):
        if subtype is None:
            return rules.rules.get(tag)
        rule = rules.rules.get(tag, {})
        return Rule(
            tag=tag,
            length=rule.material_types.get(subtype, {}).get("length"),
            values=rule.material_types.get(subtype, {}).get("values"),
            repeatable=rule.repeatable,
            required=rule.required,
        )

    return _get_default_rule


@pytest.fixture
def stub_record() -> PymarcRecord:
    bib = PymarcRecord()
    bib.leader = "00454cam a22001575i 4500"
    bib.add_field(PymarcField(tag="001", data="on1381158740"))
    bib.add_field(
        PymarcField(tag="008", data="190306s2017    ht a   j      000 1 hat d")
    )
    bib.add_field(
        PymarcField(
            tag="050",
            indicators=(" ", "4"),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="F00"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="245",
            indicators=("0", "0"),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="Title :"),
                PymarcSubfield(
                    code="b",
                    value="subtitle /",
                ),
                PymarcSubfield(
                    code="c",
                    value="Author",
                ),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="300",
            indicators=(" ", " "),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="100 pages :"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="910",
            indicators=(" ", " "),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="RL"),
            ],
        )
    )
    return bib


@pytest.fixture
def stub_record_invalid_300(stub_record) -> PymarcField:
    stub_record.remove_fields("300")
    stub_record.add_field(
        PymarcField(
            tag="300",
            indicators=("1", "0"),  # type: ignore
            subfields=[PymarcSubfield(code="h", value="foo")],
        )
    )
    return stub_record


@pytest.fixture
def stub_invalid_record() -> PymarcRecord:
    """
    Record has the following errors:
        - LDR is missing 7 characters
        - Multiple 1xx fields are present (100 and 110)
        - There is no 245 field
        - The 006 field is too short
        - 336 field has invalid ind1 and ind2
        - 336 contains an invalid subfield ($z)
        - 600 has more than one $a
    """
    bib = PymarcRecord()
    bib.leader = "01632cam a2200529       "
    bib.add_field(PymarcField(tag="001", data="1234567890"))
    bib.add_field(PymarcField(tag="001", data="1234567890"))
    bib.add_field(PymarcField(tag="006", data="p|||||"))
    bib.add_field(
        PymarcField(tag="008", data="240911s2023    lv a     bc   000 0dlat d")
    )
    bib.add_field(
        PymarcField(
            tag="100",
            indicators=("1", ""),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="Foo"),
                PymarcSubfield(code="e", value="author"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="110",
            indicators=("1", ""),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="Bar"),
                PymarcSubfield(code="e", value="publisher"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="300",
            indicators=(" ", " "),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="100 pages :"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="336",
            indicators=("1", "1"),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="still image"),
                PymarcSubfield(code="b", value="sti"),
                PymarcSubfield(code="2", value="rdacontent"),
                PymarcSubfield(code="z", value="foo"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="600",
            indicators=("1", "0"),  # type: ignore
            subfields=[
                PymarcSubfield(code="a", value="Foo, Bar,"),
                PymarcSubfield(code="a", value="Foo, Bar,"),
                PymarcSubfield(code="d", value="2000-2020"),
            ],
        )
    )
    return bib


class TestMarcRecord:
    def test_MarcRecord(self, stub_record):
        model = MarcRecord(leader=stub_record.leader, fields=stub_record.fields)
        assert isinstance(stub_record.leader, str)
        assert list(model.model_dump().keys()) == ["leader", "fields"]

    def test_MarcRecord_model_validate(self, stub_record):
        model = MarcRecord.model_validate(stub_record, from_attributes=True)
        assert isinstance(stub_record.leader, str)
        assert list(model.model_dump().keys()) == ["leader", "fields"]

    def test_MarcRecord_model_default_values(self, stub_record):
        model = MarcRecord.model_validate(stub_record, from_attributes=True)
        assert model.model_json_schema()["properties"]["rules"].get("default") is None
        assert list(model.model_dump().keys()) == ["leader", "fields"]
        assert list(model.model_dump()["fields"][0].keys()) == ["001"]
        assert list(model.model_dump()["fields"][1].keys()) == ["008"]
        assert list(model.model_dump()["fields"][2].keys()) == ["050"]
        assert isinstance(model.fields[0], ControlField)
        assert isinstance(model.fields[1], ControlField)
        assert isinstance(model.fields[2], DataField)

    def test_MarcRecord_with_context(self, stub_record):
        context_dict = {
            "rules": {
                "910": {
                    "tag": "910",
                    "repeatable": False,
                    "ind1": ["0", "1"],
                    "ind2": ["0", "1"],
                }
            },
            "replace": True,
        }
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, context=context_dict)
        errors = e.value.errors()
        assert len(errors) == 2
        assert {
            "ctx": {
                "ind": "ind1",
                "input": " ",
                "loc": ("910", "ind1"),
                "tag": "910",
                "valid": ["0", "1"],
            },
            "input": " ",
            "loc": ("fields", "910", "ind1"),
            "msg": "910 ind1: Invalid data ( ). Indicator should be ['0', '1'].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": " ",
                "loc": ("910", "ind2"),
                "tag": "910",
                "valid": ["0", "1"],
            },
            "input": " ",
            "loc": ("fields", "910", "ind2"),
            "msg": "910 ind2: Invalid data ( ). Indicator should be ['0', '1'].",
            "type": "invalid_indicator",
        } in errors

    @pytest.mark.parametrize(
        "field_value,leader,error_msg",
        [
            (
                "a|||||||||||||||||",
                "00454nam a22000005i 4500",
                "006: Invalid character(s) '|' at position '006/15'. Valid characters are: [' '].",
            ),
            (
                "a|| |||||||||  |||",
                "00454nas a22000005i 4500",
                "006: Invalid character(s) '|' at position '006/15'. Valid characters are: [' '].",
            ),
            (
                "cax|||||||||||| | ",
                "00454ncm a22000005i 4500",
                "006: Invalid character(s) 'ax' at position '006/01-02'. Valid characters are: ['an', 'bd', 'bg', 'bl', 'bt', 'ca', 'cb', 'cc', 'cg', 'ch', 'cl', 'cn', 'co', 'cp', 'cr', 'cs', 'ct', 'cy', 'cz', 'df', 'dv', 'fg', 'fl', 'fm', 'ft', 'gm', 'hy', 'jz', 'mc', 'md', 'mi', 'mo', 'mp', 'mr', 'ms', 'mu', 'mz', 'nc', 'nn', 'op', 'or', 'ov', 'pg', 'pm', 'po', 'pp', 'pr', 'ps', 'pt', 'pv', 'rc', 'rd', 'rg', 'ri', 'rp', 'rq', 'sd', 'sg', 'sn', 'sp', 'st', 'su', 'sy', 'tc', 'tl', 'ts', 'uu', 'vi', 'vr', 'wz', 'za', 'zz', '||'].",
            ),
            (
                "e||||ay |  || | ||",
                "00454nem a22000005i 4500",
                "006: Invalid character(s) 'ay' at position '006/05-06'. Valid characters are: ['  ', 'aa', 'ab', 'ac', 'ad', 'ae', 'af', 'ag', 'am', 'an', 'ap', 'au', 'az', 'ba', 'bb', 'bc', 'bd', 'be', 'bf', 'bg', 'bh', 'bi', 'bj', 'bk', 'bl', 'bo', 'br', 'bs', 'bu', 'bz', 'ca', 'cb', 'cc', 'ce', 'cp', 'cu', 'cz', 'da', 'db', 'dc', 'dd', 'de', 'df', 'dg', 'dh', 'dl', 'zz', '||'].",
            ),
            (
                "g||| |     ||  |||",
                "00454ngm a22000005i 4500",
                "006: Invalid character(s) '|' at position '006/15'. Valid characters are: [' '].",
            ),
            (
                "m||||||||||||||||a",
                "00454nmm a22000005i 4500",
                "006: Invalid character(s) 'a' at position '006/17'. Valid characters are: [' ', '|'].",
            ),
            (
                "p     |        |  ",
                "00454npm a22000005i 4500",
                "006: Invalid character(s) '|' at position '006/15'. Valid characters are: [' '].",
            ),
        ],
    )
    def test_MarcRecord_006_errors(self, stub_record, field_value, leader, error_msg):
        stub_record.remove_fields("006", "008")
        stub_record.leader = leader
        stub_record.add_field(PymarcField(tag="006", data=field_value))
        stub_record.add_field(
            PymarcField(tag="008", data=f"200101s2020    nyu{field_value[1:]}|||||")
        )
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 2
        assert errors[0]["type"] == "invalid_fixed_field"
        assert errors[0]["msg"] == error_msg
        assert errors[1]["type"] == "invalid_fixed_field"
        assert "008: Invalid character(s) " in errors[1]["msg"]

    @pytest.mark.parametrize(
        "field_value, error_msg",
        [
            (
                "ad aauuz",
                "007: Invalid character(s) 'z' at position '007/07'. Valid characters are: ['a', 'b', 'm', 'n', '|'].",
            ),
            (
                "c| ||||||||||z",
                "007: Invalid character(s) 'z' at position '007/13'. Valid characters are: ['a', 'n', 'p', 'r', 'u', '|'].",
            ),
            (
                "d| z||",
                "007: Invalid character(s) 'z' at position '007/03'. Valid characters are: ['a', 'c', '|'].",
            ),
            (
                "f|z|||||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "g|z||||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "h|z|||000||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "k|z|||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "m|z||||||||||||||000000",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "oz",
                "007: Invalid character(s) 'z' at position '007/01'. Valid characters are: ['u', '|'].",
            ),
            (
                "qz",
                "007: Invalid character(s) 'z' at position '007/01'. Valid characters are: ['u', '|'].",
            ),
            (
                "r|z||||||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "s|z|||||||||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "tt",
                "007: Invalid character(s) 't' at position '007/01'. Valid characters are: ['a', 'b', 'c', 'd', 'u', 'z', '|'].",
            ),
            (
                "v|z||||||",
                "007: Invalid character(s) 'z' at position '007/02'. Valid characters are: [' '].",
            ),
            (
                "za",
                "007: Invalid character(s) 'a' at position '007/01'. Valid characters are: ['m', 'u', 'z', '|'].",
            ),
        ],
    )
    def test_MarcRecord_007_errors(self, stub_record, field_value, error_msg):
        stub_record.add_field(PymarcField(tag="007", data=field_value))
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "invalid_fixed_field"
        assert errors[0]["msg"] == error_msg

    @pytest.mark.parametrize(
        "field_value,leader,error_msg",
        [
            (
                "250101s2020    nyu||||||||||||||||||||||",
                "00454nam a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyu|| |||||||||  ||||||||",
                "00454nas a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyu|||||||||||||||| |||||",
                "00454ncm a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyu|||||| |  || |||||||||",
                "00454nem a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyu||| |     ||  ||||||||",
                "00454ngm a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyu||||||||||||||||a|||||",
                "00454nmm a22000005i 4500",
                "008: Invalid character(s) 'a' at position '008/34'. Valid characters are: [' ', '|'].",
            ),
            (
                "250101s2020    nyu     |        |  |||||",
                "00454npm a22000005i 4500",
                "008: Invalid character(s) '|' at position '008/32'. Valid characters are: [' '].",
            ),
            (
                "250101s2020    nyy|||||||||||||| |||||||",
                "00454nam a22000005i 4500",
                "008: Invalid character(s) 'nyy' at position '008/15-17'. Valid characters are: see https://id.loc.gov/vocabulary/countries.html for list of valid country codes.",
            ),
            (
                "250101s2020    nyu|||||||||||||| ||zzz||",
                "00454nam a22000005i 4500",
                "008: Invalid character(s) 'zzz' at position '008/35-37'. Valid characters are: see https://id.loc.gov/vocabulary/languages.html for list of valid language codes.",
            ),
        ],
    )
    def test_MarcRecord_008_errors(self, stub_record, field_value, leader, error_msg):
        stub_record.remove_fields("008")
        stub_record.leader = leader
        stub_record.add_field(PymarcField(tag="008", data=field_value))
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 1
        assert errors[0]["type"] == "invalid_fixed_field"
        assert errors[0]["msg"] == error_msg

    def test_MarcRecord_050_errors(self, stub_record):
        stub_record["050"].add_subfield("b", "foo")
        stub_record["050"].add_subfield("b", "bar")
        stub_record["050"].add_subfield("t", "foo")
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 2
        assert {
            "ctx": {
                "code": "t",
                "input": [
                    PydanticSubfield(code="t", value="foo"),
                ],
                "loc": ("050", "t"),
                "tag": "050",
            },
            "input": [
                PydanticSubfield(code="t", value="foo"),
            ],
            "loc": ("fields", "050", "t"),
            "msg": "050 $t: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "type": "non_repeatable_subfield",
            "loc": ("fields", "050", "b"),
            "msg": "050 $b: Subfield cannot repeat.",
            "input": [
                PydanticSubfield(code="b", value="foo"),
                PydanticSubfield(code="b", value="bar"),
            ],
            "ctx": {
                "loc": ("050", "b"),
                "input": [
                    PydanticSubfield(code="b", value="foo"),
                    PydanticSubfield(code="b", value="bar"),
                ],
                "tag": "050",
                "code": "b",
            },
        } in errors

    def test_MarcRecord_invalid_leader(self, stub_record):
        with pytest.raises(ValidationError) as e:
            MarcRecord(leader="xxxxxcam a22001575i 4500", fields=stub_record.fields)
        errors = e.value.errors()
        assert len(errors) == 5
        assert [i["type"] for i in errors] == [
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
        ]
        assert [i["loc"] for i in errors] == [
            ("leader", "00"),
            ("leader", "01"),
            ("leader", "02"),
            ("leader", "03"),
            ("leader", "04"),
        ]

    def test_MarcRecord_invalid_leader_model_validate(self, stub_record):
        stub_record.leader = "xxxxxcam a22001575i 4500"
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 5
        assert [i["type"] for i in errors] == [
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
            "invalid_leader",
        ]
        assert [i["loc"] for i in errors] == [
            ("leader", "00"),
            ("leader", "01"),
            ("leader", "02"),
            ("leader", "03"),
            ("leader", "04"),
        ]

    def test_MarcRecord_nr_field_error(self, stub_record):
        stub_record.add_field(PymarcField(tag="001", data="foo"))
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        error = e.value.errors()[0]
        assert len(e.value.errors()) == 1
        assert error == {
            "type": "non_repeatable_field",
            "loc": ("fields", "001"),
            "msg": "001: Has been marked as a non-repeating field.",
            "input": "001",
            "ctx": {"input": "001"},
        }

    def test_MarcRecord_missing_245(self, stub_record):
        stub_record.remove_fields("245")
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        error = e.value.errors()[0]
        assert len(e.value.errors()) == 1
        assert error == {
            "ctx": {
                "input": "245",
            },
            "input": "245",
            "loc": (
                "fields",
                "245",
            ),
            "msg": "One 245 field must be present in a MARC21 record.",
            "type": "missing_required_field",
        }

    def test_MarcRecord_multiple_1xx(self, stub_record):
        stub_record.add_ordered_field(
            PymarcField(
                tag="100",
                indicators=("0", ""),
                subfields=[PymarcSubfield(code="a", value="foo")],
            )
        )
        stub_record.add_ordered_field(
            PymarcField(
                tag="110",
                indicators=("0", ""),
                subfields=[PymarcSubfield(code="a", value="bar")],
            )
        )
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        error = e.value.errors()[0]
        assert len(e.value.errors()) == 1
        assert error == {
            "ctx": {
                "input": ["100", "110"],
            },
            "input": ["100", "110"],
            "loc": ("fields", "100", "110"),
            "msg": "1XX: Only one 1XX tag is allowed. Record contains: ['100', '110']",
            "type": "multiple_1xx_fields",
        }
        assert error["type"] == "multiple_1xx_fields"
        assert error["loc"] == ("fields", "100", "110")
        assert (
            error["msg"]
            == "1XX: Only one 1XX tag is allowed. Record contains: ['100', '110']"
        )

    def test_MarcRecord_multiple_errors(self, stub_invalid_record):
        record = stub_invalid_record.as_marc21()
        reader = MARCReader(record)
        record = next(reader)
        with pytest.raises(ValidationError) as e:
            MarcRecord(leader=record.leader, fields=record.fields)
        errors = e.value.errors()
        assert len(errors) == 12
        assert {
            "ctx": {
                "input": "245",
            },
            "input": "245",
            "loc": (
                "fields",
                "245",
            ),
            "msg": "One 245 field must be present in a MARC21 record.",
            "type": "missing_required_field",
        } in errors
        assert {
            "ctx": {
                "input": "p|||||",
                "length": 6,
                "tag": "006",
                "valid": 18,
            },
            "input": "p|||||",
            "loc": ("fields", "006"),
            "msg": "006: Length appears to be invalid. Reported length is: 6. Expected length is: 18",
            "type": "control_field_length_invalid",
        } in errors
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "1",
                "loc": ("336", "ind1"),
                "tag": "336",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "336", "ind1"),
            "msg": "336 ind1: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "1",
                "loc": ("336", "ind2"),
                "tag": "336",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "336", "ind2"),
            "msg": "336 ind2: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "z",
                "input": [
                    PydanticSubfield(code="z", value="foo"),
                ],
                "loc": ("336", "z"),
                "tag": "336",
            },
            "input": [
                PydanticSubfield(code="z", value="foo"),
            ],
            "loc": ("fields", "336", "z"),
            "msg": "336 $z: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "type": "non_repeatable_field",
            "loc": ("fields", "001"),
            "msg": "001: Has been marked as a non-repeating field.",
            "input": "001",
            "ctx": {"input": "001"},
        } in errors
        assert {
            "ctx": {
                "input": ["100", "110"],
            },
            "input": ["100", "110"],
            "loc": ("fields", "100", "110"),
            "msg": "1XX: Only one 1XX tag is allowed. Record contains: ['100', '110']",
            "type": "multiple_1xx_fields",
        } in errors
        assert {
            "type": "non_repeatable_subfield",
            "loc": ("fields", "600", "a"),
            "msg": "600 $a: Subfield cannot repeat.",
            "input": [
                PydanticSubfield(code="a", value="Foo, Bar,"),
                PydanticSubfield(code="a", value="Foo, Bar,"),
            ],
            "ctx": {
                "loc": ("600", "a"),
                "input": [
                    PydanticSubfield(code="a", value="Foo, Bar,"),
                    PydanticSubfield(code="a", value="Foo, Bar,"),
                ],
                "tag": "600",
                "code": "a",
            },
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "20"),
            "msg": "LDR: Invalid character ' ' at position 'leader/20'. Valid characters are: ['4'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "20", "valid": ["4"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "21"),
            "msg": "LDR: Invalid character ' ' at position 'leader/21'. Valid characters are: ['5'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "21", "valid": ["5"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "22"),
            "msg": "LDR: Invalid character ' ' at position 'leader/22'. Valid characters are: ['0'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "22", "valid": ["0"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "23"),
            "msg": "LDR: Invalid character ' ' at position 'leader/23'. Valid characters are: ['0'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "23", "valid": ["0"]},
        } in errors

    def test_MarcRecord_multiple_errors_model_validate(self, stub_invalid_record):
        record = stub_invalid_record.as_marc21()
        reader = MARCReader(record)
        record = next(reader)
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 12
        assert {
            "ctx": {
                "input": "245",
            },
            "input": "245",
            "loc": (
                "fields",
                "245",
            ),
            "msg": "One 245 field must be present in a MARC21 record.",
            "type": "missing_required_field",
        } in errors
        assert {
            "ctx": {
                "input": "p|||||",
                "length": 6,
                "tag": "006",
                "valid": 18,
            },
            "input": "p|||||",
            "loc": ("fields", "006"),
            "msg": "006: Length appears to be invalid. Reported length is: 6. Expected length is: 18",
            "type": "control_field_length_invalid",
        } in errors
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "1",
                "loc": ("336", "ind1"),
                "tag": "336",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "336", "ind1"),
            "msg": "336 ind1: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "1",
                "loc": ("336", "ind2"),
                "tag": "336",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "336", "ind2"),
            "msg": "336 ind2: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "z",
                "input": [
                    PydanticSubfield(code="z", value="foo"),
                ],
                "loc": ("336", "z"),
                "tag": "336",
            },
            "input": [
                PydanticSubfield(code="z", value="foo"),
            ],
            "loc": ("fields", "336", "z"),
            "msg": "336 $z: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "type": "non_repeatable_field",
            "loc": ("fields", "001"),
            "msg": "001: Has been marked as a non-repeating field.",
            "input": "001",
            "ctx": {"input": "001"},
        } in errors
        assert {
            "ctx": {
                "input": ["100", "110"],
            },
            "input": ["100", "110"],
            "loc": ("fields", "100", "110"),
            "msg": "1XX: Only one 1XX tag is allowed. Record contains: ['100', '110']",
            "type": "multiple_1xx_fields",
        } in errors
        assert {
            "type": "non_repeatable_subfield",
            "loc": ("fields", "600", "a"),
            "msg": "600 $a: Subfield cannot repeat.",
            "input": [
                PydanticSubfield(code="a", value="Foo, Bar,"),
                PydanticSubfield(code="a", value="Foo, Bar,"),
            ],
            "ctx": {
                "loc": ("600", "a"),
                "input": [
                    PydanticSubfield(code="a", value="Foo, Bar,"),
                    PydanticSubfield(code="a", value="Foo, Bar,"),
                ],
                "tag": "600",
                "code": "a",
            },
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "20"),
            "msg": "LDR: Invalid character ' ' at position 'leader/20'. Valid characters are: ['4'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "20", "valid": ["4"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "21"),
            "msg": "LDR: Invalid character ' ' at position 'leader/21'. Valid characters are: ['5'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "21", "valid": ["5"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "22"),
            "msg": "LDR: Invalid character ' ' at position 'leader/22'. Valid characters are: ['0'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "22", "valid": ["0"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "23"),
            "msg": "LDR: Invalid character ' ' at position 'leader/23'. Valid characters are: ['0'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "23", "valid": ["0"]},
        } in errors


class TestMarcRecordCustomRulesAsContext:
    """
    The test record used in these tests (stub_record_invalid_300) contains the
    following fields and errors:
        leader: valid
        001:
            valid
        008:
            valid
        245:
            valid
        300:
            invalid values for ind1 ("1") and ind2 ("0"). contains invalid
            subfield "h".
        910:
            valid
    """

    def test_default_rules(self, stub_record_invalid_300):
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record_invalid_300)
        errors = e.value.errors()
        assert len(errors) == 3
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "1",
                "loc": ("300", "ind1"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "300", "ind1"),
            "msg": "300 ind1: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "0",
                "loc": ("300", "ind2"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "0",
            "loc": ("fields", "300", "ind2"),
            "msg": "300 ind2: Invalid data (0). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "h",
                "input": [
                    PydanticSubfield(code="h", value="foo"),
                ],
                "loc": ("300", "h"),
                "tag": "300",
            },
            "input": [
                PydanticSubfield(code="h", value="foo"),
            ],
            "loc": ("fields", "300", "h"),
            "msg": "300 $h: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors

    def test_custom_rules_replace_all_false(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": False,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 30,
                    "required": True,
                }
            },
        }
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record_invalid_300, context=custom_rules)
        errors = e.value.errors()
        assert len(errors) == 4
        assert {
            "ctx": {
                "input": "190306s2017    ht a   j      000 1 hat d",
                "length": 40,
                "tag": "008",
                "valid": 30,
            },
            "input": "190306s2017    ht a   j      000 1 hat d",
            "loc": ("fields", "008"),
            "msg": "008: Length appears to be invalid. Reported length is: 40. Expected length is: 30",
            "type": "control_field_length_invalid",
        } in errors
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "1",
                "loc": ("300", "ind1"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "300", "ind1"),
            "msg": "300 ind1: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "0",
                "loc": ("300", "ind2"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "0",
            "loc": ("fields", "300", "ind2"),
            "msg": "300 ind2: Invalid data (0). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "h",
                "input": [
                    PydanticSubfield(code="h", value="foo"),
                ],
                "loc": ("300", "h"),
                "tag": "300",
            },
            "input": [
                PydanticSubfield(code="h", value="foo"),
            ],
            "loc": ("fields", "300", "h"),
            "msg": "300 $h: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors

    def test_custom_rules_replace_existing(self, stub_record_invalid_300):
        custom_rules = {
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 30,
                    "required": True,
                },
                "245": {
                    "tag": "245",
                    "repeatable": False,
                    "ind1": [" ", ""],
                    "ind2": [" ", ""],
                    "subfields": {
                        "valid": ["p", "s"],
                        "repeatable": ["p"],
                        "non_repeatable": ["s"],
                    },
                    "length": None,
                    "required": True,
                },
            }
        }
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record_invalid_300, context=custom_rules)
        errors = e.value.errors()
        assert len(errors) == 9
        assert {
            "ctx": {
                "input": "190306s2017    ht a   j      000 1 hat d",
                "length": 40,
                "tag": "008",
                "valid": 30,
            },
            "input": "190306s2017    ht a   j      000 1 hat d",
            "loc": ("fields", "008"),
            "msg": "008: Length appears to be invalid. Reported length is: 40. Expected length is: 30",
            "type": "control_field_length_invalid",
        } in errors
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "0",
                "loc": ("245", "ind1"),
                "tag": "245",
                "valid": [" ", ""],
            },
            "input": "0",
            "loc": ("fields", "245", "ind1"),
            "msg": "245 ind1: Invalid data (0). Indicator should be [' ', ''].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "0",
                "loc": ("245", "ind2"),
                "tag": "245",
                "valid": [" ", ""],
            },
            "input": "0",
            "loc": ("fields", "245", "ind2"),
            "msg": "245 ind2: Invalid data (0). Indicator should be [' ', ''].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "a",
                "input": [
                    PydanticSubfield(code="a", value="Title :"),
                ],
                "loc": ("245", "a"),
                "tag": "245",
            },
            "input": [
                PydanticSubfield(code="a", value="Title :"),
            ],
            "loc": ("fields", "245", "a"),
            "msg": "245 $a: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "ctx": {
                "code": "b",
                "input": [
                    PydanticSubfield(code="b", value="subtitle /"),
                ],
                "loc": ("245", "b"),
                "tag": "245",
            },
            "input": [
                PydanticSubfield(code="b", value="subtitle /"),
            ],
            "loc": ("fields", "245", "b"),
            "msg": "245 $b: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "ctx": {
                "code": "c",
                "input": [
                    PydanticSubfield(code="c", value="Author"),
                ],
                "loc": ("245", "c"),
                "tag": "245",
            },
            "input": [
                PydanticSubfield(code="c", value="Author"),
            ],
            "loc": ("fields", "245", "c"),
            "msg": "245 $c: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors
        assert {
            "ctx": {
                "ind": "ind1",
                "input": "1",
                "loc": ("300", "ind1"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "1",
            "loc": ("fields", "300", "ind1"),
            "msg": "300 ind1: Invalid data (1). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "ind": "ind2",
                "input": "0",
                "loc": ("300", "ind2"),
                "tag": "300",
                "valid": ["", " "],
            },
            "input": "0",
            "loc": ("fields", "300", "ind2"),
            "msg": "300 ind2: Invalid data (0). Indicator should be ['', ' '].",
            "type": "invalid_indicator",
        } in errors
        assert {
            "ctx": {
                "code": "h",
                "input": [
                    PydanticSubfield(code="h", value="foo"),
                ],
                "loc": ("300", "h"),
                "tag": "300",
            },
            "input": [
                PydanticSubfield(code="h", value="foo"),
            ],
            "loc": ("fields", "300", "h"),
            "msg": "300 $h: Subfield cannot be defined in this field.",
            "type": "subfield_not_allowed",
        } in errors

    def test_custom_rules_replace_all_true(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": True,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 30,
                    "required": True,
                }
            },
        }
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record_invalid_300, context=custom_rules)
        errors = e.value.errors()
        assert len(errors) == 1
        assert {
            "ctx": {
                "input": "190306s2017    ht a   j      000 1 hat d",
                "length": 40,
                "tag": "008",
                "valid": 30,
            },
            "input": "190306s2017    ht a   j      000 1 hat d",
            "loc": ("fields", "008"),
            "msg": "008: Length appears to be invalid. Reported length is: 40. Expected length is: 30",
            "type": "control_field_length_invalid",
        } in errors


class TestMarcRecordCustomRulesPassedToModel:
    def test_custom_rules_dict(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": False,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 40,
                    "required": True,
                }
            },
        }
        data = {
            "rules": custom_rules,
            "leader": stub_record_invalid_300.leader,
            "fields": stub_record_invalid_300.fields,
        }
        model = MarcRecord.model_validate(data)
        assert list(model.model_dump().keys()) == ["leader", "fields"]
        assert list(model.model_dump()["fields"][0].keys()) == ["001"]
        assert list(model.model_dump()["fields"][1].keys()) == ["008"]
        assert list(model.model_dump()["fields"][2].keys()) == ["050"]

    def test_custom_rule_set(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": False,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 40,
                    "required": True,
                }
            },
        }
        model = MarcRecord(
            leader=stub_record_invalid_300.leader,
            fields=stub_record_invalid_300.fields,
            rules=custom_rules,
        )
        assert list(model.model_dump().keys()) == ["leader", "fields"]
        assert list(model.model_dump()["fields"][0].keys()) == ["001"]
        assert list(model.model_dump()["fields"][1].keys()) == ["008"]
        assert list(model.model_dump()["fields"][2].keys()) == ["050"]

    def test_custom_rule_dict_replace_all_true(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": True,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 40,
                    "required": True,
                }
            },
        }
        model = MarcRecord(
            leader=stub_record_invalid_300.leader,
            fields=stub_record_invalid_300.fields,
            rules=custom_rules,
        )
        assert list(model.model_dump().keys()) == ["leader", "fields"]
        assert list(model.model_dump()["fields"][0].keys()) == ["001"]
        assert list(model.model_dump()["fields"][1].keys()) == ["008"]
        assert list(model.model_dump()["fields"][2].keys()) == ["050"]

    def test_custom_rule_dict_replace_all_false(self, stub_record_invalid_300):
        custom_rules = {
            "replace_all": False,
            "rules": {
                "008": {
                    "tag": "008",
                    "repeatable": False,
                    "ind1": None,
                    "ind2": None,
                    "subfields": None,
                    "length": 30,
                    "required": True,
                }
            },
        }
        data = {
            "rules": custom_rules,
            "leader": stub_record_invalid_300.leader,
            "fields": stub_record_invalid_300.fields,
        }
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(data)
        errors = e.value.errors()
        assert len(errors) == 1
        assert {
            "ctx": {
                "input": "190306s2017    ht a   j      000 1 hat d",
                "length": 40,
                "tag": "008",
                "valid": 30,
            },
            "input": "190306s2017    ht a   j      000 1 hat d",
            "loc": ("fields", "008"),
            "msg": "008: Length appears to be invalid. Reported length is: 40. Expected length is: 30",
            "type": "control_field_length_invalid",
        } in errors

    def test_no_marc_rules(self, stub_record_invalid_300):
        data = {
            "rules": None,
            "leader": stub_record_invalid_300.leader,
            "fields": stub_record_invalid_300.fields,
        }
        model = MarcRecord.model_validate(data)
        assert model.model_dump()["fields"][-1] == {
            "300": {"ind1": "1", "ind2": "0", "subfields": [{"h": "foo"}]}
        }


class TestControlField:
    @pytest.mark.parametrize(
        "tag, subtype, data",
        [
            ("001", None, "ocn123456789"),
            ("003", None, "OCoLC"),
            ("005", None, "20241111111111.0"),
            ("006", "BK", "a|||||||||||||| ||"),
            ("007", "c", "cr |||||||||||"),
            ("008", "BK", "210505s2021    nyu           000 0 eng d"),
            ("009", None, "foo"),
        ],
    )
    def test_ControlField_valid(self, tag, data, subtype, get_default_rule):
        model = ControlField(tag=tag, data=data, rules=get_default_rule(tag, subtype))
        assert model.model_dump(by_alias=True) == {tag: data}
        assert model.model_json_schema()["properties"]["rules"].get("default") is None

    @pytest.mark.parametrize(
        "data",
        ["cr |||||||||||", "ad |||||"],
    )
    def test_ControlField_007(self, data, get_default_rule):
        model = ControlField(
            tag="007", data=data, rules=get_default_rule("007", data[0])
        )
        assert model.model_dump(by_alias=True) == {"007": data}
        assert model.model_json_schema()["properties"]["rules"].get("default") is None

    def test_ControlField_valid_with_rules(self):
        rule = {
            "tag": "005",
            "repeatable": False,
            "ind1": None,
            "ind2": None,
            "subfields": None,
            "length": 16,
        }
        model = ControlField(tag="005", data="20241111111111.0", rules=rule)
        assert model.model_dump(by_alias=True) == {"005": "20241111111111.0"}

    @pytest.mark.parametrize(
        "tag",
        [
            "001",
            "003",
            "005",
            "006",
            "007",
            "007",
        ],
    )
    @pytest.mark.parametrize(
        "field_value",
        [
            1,
            1.0,
            None,
            [],
        ],
    )
    def test_ControlField_data_string_type_error(
        self, tag, field_value, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(tag=tag, data=field_value, rules=get_default_rule(tag))
        assert e.value.errors()[0]["type"] == "string_type"
        assert e.value.errors()[0]["loc"] == ("data",)
        assert len(e.value.errors()) == 1

    @pytest.mark.parametrize(
        "field_value, error_type",
        [
            ("2024", "control_field_length_invalid"),
            ("b|", "control_field_length_invalid"),
            ("b||||||||||||||||||||", "control_field_length_invalid"),
        ],
    )
    def test_ControlField_006_field_control_field_length_invalid(
        self, field_value, error_type, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(
                tag="006", data=field_value, rules=get_default_rule("006", "BK")
            )
        assert e.value.errors()[0]["type"] == error_type
        assert e.value.errors()[0]["loc"] == ("data", "006")
        assert len(e.value.errors()) == 1

    @pytest.mark.parametrize(
        "field_value, error_msg",
        [
            (
                "a||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 8",
            ),
            (
                "c||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 14",
            ),
            (
                "d||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 6",
            ),
            (
                "f||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 10",
            ),
            (
                "g||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 9",
            ),
            (
                "h||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 13",
            ),
            (
                "k||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 6",
            ),
            (
                "m||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 23",
            ),
            (
                "o||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 2",
            ),
            (
                "q||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 2",
            ),
            (
                "r||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 11",
            ),
            (
                "s||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 14",
            ),
            (
                "t||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 2",
            ),
            (
                "v||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 9",
            ),
            (
                "z||",
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: 2",
            ),
        ],
    )
    def test_ControlField_007_control_field_length_invalid(
        self, field_value, error_msg, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(
                tag="007",
                data=field_value,
                rules=get_default_rule("007", field_value[0]),
            )
        assert e.value.errors()[0]["type"] == "control_field_length_invalid"
        assert e.value.errors()[0]["msg"] == error_msg
        assert len(e.value.errors()) == 1

    @pytest.mark.parametrize(
        "field_value, error_type",
        [
            ("210505s2021    nyu", "control_field_length_invalid"),
            (
                "20210505s2021    nyu           000 0 eng d",
                "control_field_length_invalid",
            ),
        ],
    )
    def test_ControlField_008_field_control_field_length_invalid(
        self, field_value, error_type, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(
                tag="008", data=field_value, rules=get_default_rule("008", "BK")
            )
        assert e.value.errors()[0]["type"] == error_type
        assert e.value.errors()[0]["loc"] == ("data", "008")
        assert len(e.value.errors()) == 1


class TestDataField:
    def test_DataField_010_valid(self, get_default_rule):
        model = DataField(
            tag="010",
            indicators=("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
                PymarcSubfield(code="z", value="2020111111"),
            ],
            rules=get_default_rule("010"),
        )
        assert model.model_dump() == {
            "010": {
                "ind1": "",
                "ind2": "",
                "subfields": [{"a": "2024111111"}, {"z": "2020111111"}],
            }
        }
        assert model.indicators[0] == ""
        assert model.indicators[1] == ""

    @pytest.mark.parametrize(
        "ind1_value, ind2_value",
        [
            (
                "1",
                "1",
            ),
            (
                "0",
                "0",
            ),
            (
                "2",
                "2",
            ),
        ],
    )
    def test_DataField_010_invalid_indicators(
        self, ind1_value, ind2_value, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=(ind1_value, ind2_value),
                subfields=[PymarcSubfield(code="a", value="2024111111")],
                rules=get_default_rule("010"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert len(e.value.errors()) == 2
        assert sorted(error_types) == sorted(["invalid_indicator", "invalid_indicator"])

    @pytest.mark.parametrize(
        "field_value",
        [
            1,
            1.0,
            None,
            [],
        ],
    )
    def test_DataField_010_invalid_type(self, field_value, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=("", ""),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
                rules=get_default_rule("010"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_010_repeated_subfield_error(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=(
                    "",
                    "",
                ),
                subfields=[
                    PymarcSubfield(code="a", value="2024111111"),
                    PymarcSubfield(code="a", value="2025111111"),
                ],
                rules=get_default_rule("010"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_010_subfield_not_allowed(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=(
                    "",
                    "",
                ),
                subfields=[PymarcSubfield(code="c", value="2024111111")],
                rules=get_default_rule("010"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "010", "c")])
        assert len(e.value.errors()) == 1

    def test_DataField_020_valid(self, get_default_rule):
        model = DataField(
            tag="020",
            indicators=("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
            ],
            rules=get_default_rule("020"),
        )
        assert model.model_dump() == {
            "020": {"ind1": "", "ind2": "", "subfields": [{"a": "2024111111"}]}
        }
        assert model.indicators[0] == ""
        assert model.indicators[1] == ""

    @pytest.mark.parametrize(
        "ind1_value, ind2_value",
        [
            (
                "1",
                "1",
            ),
            (
                "0",
                "0",
            ),
            (
                "2",
                "2",
            ),
        ],
    )
    def test_DataField_020_invalid_indicators(
        self, ind1_value, ind2_value, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=(ind1_value, ind2_value),
                subfields=[PymarcSubfield(code="a", value="2024111111")],
                rules=get_default_rule("020"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert len(e.value.errors()) == 2
        assert sorted(error_types) == sorted(["invalid_indicator", "invalid_indicator"])

    @pytest.mark.parametrize(
        "field_value",
        [
            1,
            1.0,
            None,
            [],
        ],
    )
    def test_DataField_020_invalid_type(self, field_value, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=("", ""),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
                rules=get_default_rule("020"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_020_repeated_subfield_error(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=(
                    "",
                    "",
                ),
                subfields=[
                    PymarcSubfield(code="a", value="2024111111"),
                    PymarcSubfield(code="a", value="2024111111"),
                ],
                rules=get_default_rule("020"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_020_subfield_not_allowed(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=(
                    "",
                    "",
                ),
                subfields=[PymarcSubfield(code="t", value="2024111111")],
                rules=get_default_rule("020"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "020", "t")])
        assert len(e.value.errors()) == 1

    def test_DataField_050_valid(self, get_default_rule):
        model = DataField(
            tag="050",
            indicators=("0", "4"),
            subfields=[
                PymarcSubfield(code="a", value="F00"),
            ],
            rules=get_default_rule("050"),
        )
        assert model.model_dump() == {
            "050": {"ind1": "0", "ind2": "4", "subfields": [{"a": "F00"}]}
        }
        assert model.indicators[0] == "0"
        assert model.indicators[1] == "4"

    @pytest.mark.parametrize(
        "ind1_value, ind2_value",
        [
            (
                "5",
                "6",
            ),
            (
                "7",
                "8",
            ),
            (
                "9",
                "1",
            ),
        ],
    )
    def test_DataField_050_invalid_indicators(
        self, ind1_value, ind2_value, get_default_rule
    ):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=(ind1_value, ind2_value),
                subfields=[PymarcSubfield(code="a", value="F00")],
                rules=get_default_rule("050"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert len(e.value.errors()) == 2
        assert sorted(error_types) == sorted(["invalid_indicator", "invalid_indicator"])

    @pytest.mark.parametrize(
        "field_value",
        [
            1,
            1.0,
            None,
            [],
        ],
    )
    def test_DataField_050_invalid_type(self, field_value, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=("0", "4"),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
                rules=get_default_rule("050"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_050_repeated_subfield_error(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=(
                    "0",
                    "4",
                ),
                subfields=[
                    PymarcSubfield(code="a", value="F00"),
                    PymarcSubfield(code="a", value="F00"),
                    PymarcSubfield(code="b", value="B11"),
                    PymarcSubfield(code="b", value="B11"),
                ],
                rules=get_default_rule("050"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_050_subfield_not_allowed(self, get_default_rule):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=(
                    "0",
                    "4",
                ),
                subfields=[PymarcSubfield(code="t", value="F00")],
                rules=get_default_rule("050"),
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "050", "t")])
        assert len(e.value.errors()) == 1

    def test_DataField_900_valid(self, get_default_rule):
        model = DataField(
            tag="900",
            indicators=("", ""),
            subfields=[
                PymarcSubfield(code="a", value="Foo"),
            ],
            rules=get_default_rule("900"),
        )
        assert model.model_dump() == {
            "900": {"ind1": "", "ind2": "", "subfields": [{"a": "Foo"}]}
        }
        assert model.indicators[0] == ""
        assert model.indicators[1] == ""

    @pytest.mark.parametrize(
        "field_value",
        [
            1,
            1.0,
            None,
            [],
        ],
    )
    def test_DataField_900_invalid_type(self, field_value):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="900",
                indicators=(" ", " "),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types


class TestPydanticIndicators:
    @pytest.mark.parametrize(
        "first, second",
        [
            ("0", "1"),
            ("", " "),
            (" ", "5"),
        ],
    )
    def test_PydanticIndicators_valid(self, first, second):
        model = PydanticIndicators(first=first, second=second)
        assert model.model_dump(by_alias=True) == (first, second)
        assert model[0] == first
        assert model[1] == second

    @pytest.mark.parametrize(
        "first, second, errors",
        [
            ("10", "100", ["string_too_long", "string_too_long"]),
            (4, [], ["string_type", "string_type"]),
            (2.0, {}, ["string_type", "string_type"]),
        ],
    )
    def test_PydanticIndicators_invalid(self, first, second, errors):
        with pytest.raises(ValidationError) as e:
            PydanticIndicators(first=first, second=second)
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(errors)


class TestPydanticSubfield:
    @pytest.mark.parametrize(
        "code, value",
        [
            ("a", "foo"),
            ("b", "bar"),
            ("8", "baz"),
        ],
    )
    def test_PydanticSubfield_valid(self, code, value):
        model = PydanticSubfield(code=code, value=value)
        assert model.model_dump(by_alias=True) == {code: value}

    @pytest.mark.parametrize(
        "code, value, errors",
        [
            ("10", 4, ["string_too_long", "string_type"]),
            (4, [], ["string_type", "string_type"]),
            (2.0, {}, ["string_type", "string_type"]),
        ],
    )
    def test_PydanticSubfield_invalid(self, code, value, errors):
        with pytest.raises(ValidationError) as e:
            PydanticSubfield(code=code, value=value)
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(errors)
