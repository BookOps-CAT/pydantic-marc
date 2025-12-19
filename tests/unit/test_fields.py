import pytest
from pydantic import ValidationError
from pymarc import Indicators as PymarcIndicators
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.components import PydanticIndicators, PydanticSubfield
from pydantic_marc.fields import ControlField, DataField


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
            indicators=PymarcIndicators("", ""),
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
                indicators=PymarcIndicators(ind1_value, ind2_value),
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
                indicators=PymarcIndicators("", ""),
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
            indicators=PymarcIndicators("", ""),
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
                indicators=PymarcIndicators(ind1_value, ind2_value),
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
                indicators=PymarcIndicators("", ""),
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
            indicators=PymarcIndicators("0", "4"),
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
                indicators=PymarcIndicators(ind1_value, ind2_value),
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
                indicators=PymarcIndicators("0", "4"),
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
            indicators=PymarcIndicators("", ""),
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
                indicators=PymarcIndicators(" ", " "),
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
