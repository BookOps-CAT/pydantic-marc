import pytest
from pydantic import ValidationError
from pymarc import Field as PymarcField
from pymarc import Indicators as PymarcIndicators
from pymarc import Leader as PymarcLeader
from pymarc import MARCReader
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.models import ControlField, DataField, MarcRecord
from pydantic_marc.rules import MARC_RULES


class TestControlField:
    @pytest.mark.parametrize(
        "tag, data",
        [
            ("001", "ocn123456789"),
            ("003", "OCoLC"),
            ("005", "20241111111111.0"),
            ("006", "a|||||||||||||||||"),
            ("007", "cr |||||||||||"),
            ("008", "210505s2021    nyu           000 0 eng d"),
        ],
    )
    def test_ControlField_valid(self, tag, data):
        model = ControlField(tag=tag, data=data)
        assert model.model_dump(by_alias=True) == {tag: data}
        assert MARC_RULES[tag] == model.rules[tag]
        assert model.model_json_schema()["properties"]["rules"].get("default") is None

    def test_ControlField_valid_with_rules(self):
        rule = {
            "005": {
                "repeatable": False,
                "ind1": None,
                "ind2": None,
                "subfields": None,
                "length": 16,
            }
        }
        model = ControlField(tag="005", data="20241111111111.0", rules=rule)
        assert model.model_dump(by_alias=True) == {"005": "20241111111111.0"}
        assert MARC_RULES["005"]["length"] is None

    @pytest.mark.parametrize(
        "tag, data",
        [
            ("001", "ocn123456789"),
            ("003", "OCoLC"),
            ("005", "20241111111111.0"),
            ("006", "a|||||||||||||||||"),
            ("007", "cr |||||||||||"),
            ("008", "210505s2021    nyu           000 0 eng d"),
        ],
    )
    def test_ControlField_valid_from_field(self, tag, data):
        field = PymarcField(tag=tag, data=data)
        model = ControlField.model_validate(field, from_attributes=True)
        assert model.model_dump(by_alias=True) == {tag: data}

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
    def test_ControlField_data_string_type_error(self, tag, field_value):
        with pytest.raises(ValidationError) as e:
            ControlField(tag=tag, data=field_value)
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
        self, field_value, error_type
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(tag="006", data=field_value)
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
                "007: Length appears to be invalid. Reported length is: 3. Expected length is: [6, 14]",
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
        self, field_value, error_msg
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(tag="007", data=field_value)
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
        self, field_value, error_type
    ):
        with pytest.raises(ValidationError) as e:
            ControlField(tag="008", data=field_value)
        assert e.value.errors()[0]["type"] == error_type
        assert e.value.errors()[0]["loc"] == ("data", "008")
        assert len(e.value.errors()) == 1


class TestDataField:
    def test_DataField_010_valid(self):
        model = DataField(
            tag="010",
            indicators=PymarcIndicators("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
                PymarcSubfield(code="z", value="2020111111"),
            ],
        )
        assert model.model_dump() == {
            "010": {
                "ind1": "",
                "ind2": "",
                "subfields": [{"a": "2024111111"}, {"z": "2020111111"}],
            }
        }

    def test_DataField_010_valid_from_field(self):
        field = PymarcField(
            tag="010",
            indicators=PymarcIndicators("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
                PymarcSubfield(code="z", value="2020111111"),
            ],
        )
        model = DataField.model_validate(field, from_attributes=True)
        assert model.model_dump() == {
            "010": {
                "ind1": "",
                "ind2": "",
                "subfields": [{"a": "2024111111"}, {"z": "2020111111"}],
            }
        }

    def test_DataField_010_valid_additional_context(self):
        field = PymarcField(
            tag="010",
            indicators=PymarcIndicators("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
                PymarcSubfield(code="z", value="2020111111"),
            ],
        )
        model = DataField.model_validate(
            field, from_attributes=True, context={"foo": "bar"}
        )
        assert model.model_dump() == {
            "010": {
                "ind1": "",
                "ind2": "",
                "subfields": [{"a": "2024111111"}, {"z": "2020111111"}],
            }
        }

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
    def test_DataField_010_invalid_indicators(self, ind1_value, ind2_value):
        field = PymarcField(
            tag="010",
            indicators=PymarcIndicators(ind1_value, ind2_value),
            subfields=[PymarcSubfield(code="a", value="2024111111")],
        )
        with pytest.raises(ValidationError) as e:
            DataField.model_validate(field, from_attributes=True)
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
    def test_DataField_010_invalid_type(self, field_value):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=PymarcIndicators("", ""),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_010_repeated_subfield_error(self):
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
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_010_subfield_not_allowed(self):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="010",
                indicators=(
                    "",
                    "",
                ),
                subfields=[PymarcSubfield(code="c", value="2024111111")],
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "010", "c")])
        assert len(e.value.errors()) == 1

    def test_DataField_020_valid(self):
        model = DataField(
            tag="020",
            indicators=PymarcIndicators("", ""),
            subfields=[
                PymarcSubfield(code="a", value="2024111111"),
            ],
        )
        assert model.model_dump() == {
            "020": {"ind1": "", "ind2": "", "subfields": [{"a": "2024111111"}]}
        }

    def test_DataField_020_valid_from_field(self):
        field = PymarcField(
            tag="020",
            indicators=PymarcIndicators("", ""),
            subfields=[PymarcSubfield(code="a", value="2024111111")],
        )
        model = DataField.model_validate(field, from_attributes=True)
        assert model.model_dump() == {
            "020": {"ind1": "", "ind2": "", "subfields": [{"a": "2024111111"}]}
        }

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
    def test_DataField_020_invalid_indicators(self, ind1_value, ind2_value):
        field = PymarcField(
            tag="020",
            indicators=PymarcIndicators(ind1_value, ind2_value),
            subfields=[PymarcSubfield(code="a", value="2024111111")],
        )
        with pytest.raises(ValidationError) as e:
            DataField.model_validate(field, from_attributes=True)
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
    def test_DataField_020_invalid_type(self, field_value):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=PymarcIndicators("", ""),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_020_repeated_subfield_error(self):
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
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_020_subfield_not_allowed(self):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="020",
                indicators=(
                    "",
                    "",
                ),
                subfields=[PymarcSubfield(code="t", value="2024111111")],
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "020", "t")])
        assert len(e.value.errors()) == 1

    def test_DataField_050_valid(self):
        model = DataField(
            tag="050",
            indicators=PymarcIndicators("0", "4"),
            subfields=[
                PymarcSubfield(code="a", value="F00"),
            ],
        )
        assert model.model_dump() == {
            "050": {"ind1": "0", "ind2": "4", "subfields": [{"a": "F00"}]}
        }

    def test_DataField_050_valid_from_field(self):
        field = PymarcField(
            tag="050",
            indicators=PymarcIndicators("0", "4"),
            subfields=[
                PymarcSubfield(code="a", value="F00"),
            ],
        )
        model = DataField.model_validate(field, from_attributes=True)
        assert model.model_dump() == {
            "050": {"ind1": "0", "ind2": "4", "subfields": [{"a": "F00"}]}
        }

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
    def test_DataField_050_invalid_indicators(self, ind1_value, ind2_value):
        field = PymarcField(
            tag="050",
            indicators=PymarcIndicators(ind1_value, ind2_value),
            subfields=[PymarcSubfield(code="a", value="F00")],
        )
        with pytest.raises(ValidationError) as e:
            DataField.model_validate(field, from_attributes=True)
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
    def test_DataField_050_invalid_type(self, field_value):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=PymarcIndicators("0", "4"),
                subfields=[
                    PymarcSubfield(code="a", value=field_value),
                ],
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert "string_type" in error_types

    def test_DataField_050_repeated_subfield_error(self):
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
            )
        error_types = [i["type"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["non_repeatable_subfield"])
        assert len(e.value.errors()) == 1

    def test_DataField_050_subfield_not_allowed(self):
        with pytest.raises(ValidationError) as e:
            DataField(
                tag="050",
                indicators=(
                    "0",
                    "4",
                ),
                subfields=[PymarcSubfield(code="t", value="F00")],
            )
        error_types = [i["type"] for i in e.value.errors()]
        error_locs = [i["loc"] for i in e.value.errors()]
        assert sorted(error_types) == sorted(["subfield_not_allowed"])
        assert sorted(error_locs) == sorted([("subfields", "050", "t")])
        assert len(e.value.errors()) == 1


class TestMarcRecord:
    def test_MarcRecord(self, stub_record):
        model = MarcRecord(leader=stub_record.leader, fields=stub_record.fields)
        assert isinstance(stub_record.leader, str)
        assert list(model.model_dump().keys()) == ["leader", "fields"]

    def test_MarcRecord_model_validate(self, stub_record):
        model = MarcRecord.model_validate(stub_record, from_attributes=True)
        assert isinstance(stub_record.leader, str)
        assert list(model.model_dump().keys()) == ["leader", "fields"]

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
            [
                ("fields", "050", "b"),
                ("fields", "050", "t"),
            ]
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
        assert error["loc"] == (
            "fields",
            "001",
        )
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
                indicators=(
                    "0",
                    "",
                ),
                subfields=[PymarcSubfield(code="a", value="foo")],
            )
        )
        stub_record.add_ordered_field(
            PymarcField(
                tag="110",
                indicators=(
                    "0",
                    "",
                ),
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
        error_types = [i["type"] for i in errors]
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
