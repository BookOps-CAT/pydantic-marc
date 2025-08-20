import pytest
from pydantic import ValidationError
from pymarc import Field as PymarcField
from pymarc import Leader as PymarcLeader
from pymarc import MARCReader
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.fields import ControlField, DataField, PydanticSubfield
from pydantic_marc.models import MarcRecord


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

    def test_MarcRecord_pymarcleader(self, stub_record):
        record = stub_record.as_marc21()
        reader = MARCReader(record)
        record = next(reader)
        model = MarcRecord.model_validate(record, from_attributes=True)
        assert isinstance(record.leader, PymarcLeader)
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

    def test_MarcRecord_006_errors(self, stub_record):
        stub_record.add_field(PymarcField(tag="006", data="a||||||||||||||||z"))
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 2
        assert {
            "type": "invalid_fixed_field",
            "loc": ("fields", "17"),
            "msg": "006: Invalid character 'z' at position '006/17'. Byte should be: [' ', 'a', 'b', 'c', 'd', '|'].",
            "input": "z",
            "ctx": {
                "tag": "006",
                "input": "z",
                "valid": [" ", "a", "b", "c", "d", "|"],
                "loc": "17",
            },
        } in errors
        assert {
            "type": "invalid_fixed_field",
            "loc": ("fields", "15"),
            "msg": "006: Invalid character '|' at position '006/15'. Byte should be: [' '].",
            "input": "|",
            "ctx": {"tag": "006", "input": "|", "valid": [" "], "loc": "15"},
        } in errors

    @pytest.mark.parametrize(
        "field_value, error_msg",
        [
            (
                "ad aauuz",
                "007: Invalid character 'z' at position '007/07'. Byte should be: ['a', 'b', 'm', 'n', '|'].",
            ),
            (
                "c| ||||||||||z",
                "007: Invalid character 'z' at position '007/13'. Byte should be: ['a', 'n', 'p', 'r', 'u', '|'].",
            ),
            (
                "d| z||",
                "007: Invalid character 'z' at position '007/03'. Byte should be: ['a', 'c', '|'].",
            ),
            (
                "f|z|||||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "g|z||||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "h|z|||000||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "k|z|||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "m|z||||||||||||||000000",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "oz",
                "007: Invalid character 'z' at position '007/01'. Byte should be: ['u', '|'].",
            ),
            (
                "qz",
                "007: Invalid character 'z' at position '007/01'. Byte should be: ['u', '|'].",
            ),
            (
                "r|z||||||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "s|z|||||||||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "tt",
                "007: Invalid character 't' at position '007/01'. Byte should be: ['a', 'b', 'c', 'd', 'u', 'z', '|'].",
            ),
            (
                "v|z||||||",
                "007: Invalid character 'z' at position '007/02'. Byte should be: [' '].",
            ),
            (
                "za",
                "007: Invalid character 'a' at position '007/01'. Byte should be: ['m', 'u', 'z', '|'].",
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
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
            ),
            (
                "250101s2020    nyu|| |||||||||  ||||||||",
                "00454nas a22000005i 4500",
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
            ),
            (
                "250101s2020    nyu|||||||||||||||| |||||",
                "00454ncm a22000005i 4500",
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
            ),
            (
                "250101s2020    nyu|||||| |  || |||||||||",
                "00454nem a22000005i 4500",
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
            ),
            (
                "250101s2020    nyu||| |     ||  ||||||||",
                "00454ngm a22000005i 4500",
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
            ),
            (
                "250101s2020    nyu||||||||||||||||a|||||",
                "00454nmm a22000005i 4500",
                "008: Invalid character 'a' at position '008/34'. Byte should be: [' ', '|'].",
            ),
            (
                "250101s2020    nyu     |        |  |||||",
                "00454npm a22000005i 4500",
                "008: Invalid character '|' at position '008/32'. Byte should be: [' '].",
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
            "msg": "LDR: Invalid character ' ' at position 'leader/20'. Byte should be: ['4'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "20", "valid": ["4"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "21"),
            "msg": "LDR: Invalid character ' ' at position 'leader/21'. Byte should be: ['5'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "21", "valid": ["5"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "22"),
            "msg": "LDR: Invalid character ' ' at position 'leader/22'. Byte should be: ['0'].",
            "input": " ",
            "ctx": {"input": " ", "loc": "22", "valid": ["0"]},
        } in errors
        assert {
            "type": "invalid_leader",
            "loc": ("leader", "23"),
            "msg": "LDR: Invalid character ' ' at position 'leader/23'. Byte should be: ['0'].",
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
