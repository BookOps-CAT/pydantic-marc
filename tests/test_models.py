import pytest
from pydantic import ValidationError
from pymarc import Field as PymarcField
from pymarc import Leader as PymarcLeader
from pymarc import MARCReader
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.fields import ControlField, DataField
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
        assert sorted([i["type"] for i in errors]) == sorted(
            ["invalid_indicator", "invalid_indicator"]
        )
        assert sorted([i["loc"] for i in errors]) == sorted(
            [("fields", "910", "ind1"), ("fields", "910", "ind2")]
        )

    def test_MarcRecord_050_errors(self, stub_record):
        stub_record["050"].add_subfield("b", "foo")
        stub_record["050"].add_subfield("b", "bar")
        stub_record["050"].add_subfield("t", "foo")
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        errors = e.value.errors()
        assert len(errors) == 2
        assert sorted([i["type"] for i in errors]) == sorted(
            ["non_repeatable_subfield", "subfield_not_allowed"]
        )
        assert sorted([i["loc"] for i in errors]) == sorted(
            [("fields", "050", "b"), ("fields", "050", "t")]
        )
        assert sorted([i["msg"] for i in errors]) == sorted(
            [
                "050 $b: Subfield cannot repeat.",
                "050 $t: Subfield cannot be defined in this field.",
            ]
        )

    def test_MarcRecord_nr_field_error(self, stub_record):
        stub_record.add_field(PymarcField(tag="001", data="foo"))
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        error = e.value.errors()[0]
        assert len(e.value.errors()) == 1
        assert error["type"] == "non_repeatable_field"
        assert error["loc"] == ("fields", "001")
        assert error["msg"] == "001: Has been marked as a non-repeating field."

    def test_MarcRecord_missing_245(self, stub_record):
        stub_record.remove_fields("245")
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record, from_attributes=True)
        error = e.value.errors()[0]
        assert len(e.value.errors()) == 1
        assert error["type"] == "missing_required_field"
        assert error["loc"] == ("fields", "245")
        assert error["msg"] == "One 245 field must be present in a MARC21 record."

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
        error_count = len(errors)
        error_types = [i["type"] for i in errors]
        error_locs = [i["loc"] for i in errors]
        assert error_count == 9
        assert sorted(error_types) == sorted(
            [
                "invalid_indicator",
                "invalid_indicator",
                "subfield_not_allowed",
                "control_field_length_invalid",
                "multiple_1xx_fields",
                "non_repeatable_subfield",
                "non_repeatable_field",
                "missing_required_field",
                "string_pattern_mismatch",
            ]
        )
        assert ("leader",) in error_locs
        assert ("fields", "001") in error_locs
        assert ("fields", "006") in error_locs
        assert ("fields", "100", "110") in error_locs
        assert ("fields", "245") in error_locs
        assert ("fields", "336", "ind1") in error_locs
        assert ("fields", "336", "ind2") in error_locs
        assert ("fields", "336", "z") in error_locs
        assert ("fields", "600", "a") in error_locs


class TestMarcRecordCustomRulesAsContext:
    def test_default_rules(self, stub_record_invalid_300):
        with pytest.raises(ValidationError) as e:
            MarcRecord.model_validate(stub_record_invalid_300)
        errors = e.value.errors()
        assert len(errors) == 3
        assert sorted([i["type"] for i in errors]) == sorted(
            ["invalid_indicator", "invalid_indicator", "subfield_not_allowed"]
        )
        assert sorted([i["loc"] for i in errors]) == sorted(
            [
                ("fields", "300", "ind1"),
                ("fields", "300", "ind2"),
                ("fields", "300", "h"),
            ]
        )

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
        assert sorted([i["type"] for i in errors]) == sorted(
            [
                "control_field_length_invalid",
                "invalid_indicator",
                "invalid_indicator",
                "subfield_not_allowed",
            ]
        )
        assert sorted([i["loc"] for i in errors]) == sorted(
            [
                ("fields", "008"),
                ("fields", "300", "ind1"),
                ("fields", "300", "ind2"),
                ("fields", "300", "h"),
            ]
        )

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
        assert sorted([i["type"] for i in errors]) == sorted(
            [
                "control_field_length_invalid",
                "invalid_indicator",
                "invalid_indicator",
                "invalid_indicator",
                "invalid_indicator",
                "subfield_not_allowed",
                "subfield_not_allowed",
                "subfield_not_allowed",
                "subfield_not_allowed",
            ]
        )
        assert sorted([i["loc"] for i in errors]) == sorted(
            [
                ("fields", "008"),
                ("fields", "245", "ind1"),
                ("fields", "245", "ind2"),
                ("fields", "245", "a"),
                ("fields", "245", "b"),
                ("fields", "245", "c"),
                ("fields", "300", "ind1"),
                ("fields", "300", "ind2"),
                ("fields", "300", "h"),
            ]
        )

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
        assert sorted([i["type"] for i in errors]) == sorted(
            ["control_field_length_invalid"]
        )
        assert sorted([i["loc"] for i in errors]) == sorted([("fields", "008")])


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
        assert sorted([i["type"] for i in errors]) == sorted(
            ["control_field_length_invalid"]
        )
        assert sorted([i["loc"] for i in errors]) == sorted([("fields", "008")])

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
