import pytest
from pymarc import Subfield as PymarcSubfield

from pydantic_marc.errors import (
    ControlFieldLength,
    InvalidIndicator,
    InvalidSubfield,
    MissingRequiredField,
    MultipleMainEntryValues,
    NonRepeatableField,
    NonRepeatableSubfield,
)


@pytest.mark.parametrize(
    "tag, input, loc, valid",
    [
        ("050", ["", " ", "0", "1"], "9", "ind1"),
        ("035", ["", " "], "2", "ind2"),
        ("040", ["", " "], "a", "ind2"),
    ],
)
def test_invalid_indicator(tag, input, loc, valid):
    error = InvalidIndicator({"valid": valid, "input": input, "loc": (tag, loc)})
    assert error.context.get("tag") == tag
    assert error.type == "invalid_indicator"
    assert (
        error.message()
        == f"{tag} {loc}: Invalid data ({input}). Indicator should be {valid}."
    )
    assert (
        error.message_template
        == "{tag} {ind}: Invalid data ({input}). Indicator should be {valid}."
    )
    assert error.error_details.get("loc") == (tag, loc)


@pytest.mark.parametrize(
    "tag, code, subfields",
    [
        (
            "010",
            "c",
            [
                PymarcSubfield(code="a", value="foo"),
                PymarcSubfield(code="c", value="bar"),
            ],
        ),
        (
            "500",
            "z",
            [
                PymarcSubfield(code="a", value="foo"),
                PymarcSubfield(code="z", value="bar"),
            ],
        ),
    ],
)
def test_invalid_subfield(tag, code, subfields):
    invalid_subfields = [i for i in subfields if i.code == code]
    error = InvalidSubfield({"loc": (tag, code), "input": invalid_subfields})
    assert error.type == "subfield_not_allowed"
    assert error.context.get("tag") == tag
    assert (
        error.message() == f"{tag} ${code}: Subfield cannot be defined in this field."
    )
    assert (
        error.message_template
        == "{tag} ${code}: Subfield cannot be defined in this field."
    )
    assert error.error_details.get("loc") == (tag, code)
    assert error.error_details.get("input") == [subfields[1]]


@pytest.mark.parametrize(
    "tag, data, valid",
    [
        (
            "006",
            "a|",
            "18",
        ),
        (
            "007",
            "a|",
            "8",
        ),
        (
            "008",
            "a|",
            "40",
        ),
    ],
)
def test_control_field_length(tag, data, valid):
    error = ControlFieldLength({"tag": tag, "valid": valid, "input": data})
    assert error.type == "control_field_length_invalid"
    assert error.context.get("tag") == tag
    assert (
        error.message()
        == f"{tag}: Length appears to be invalid. Reported length is: {len(data)}. Expected length is: {valid}"
    )
    assert (
        error.message_template
        == "{tag}: Length appears to be invalid. Reported length is: {length}. Expected length is: {valid}"
    )
    assert error.error_details.get("loc") == (tag,)
    assert error.error_details.get("input") == data


def test_multiple_main_entry_values():
    input = ["100", "110"]
    error = MultipleMainEntryValues({"input": input})
    assert error.type == "multiple_1xx_fields"
    assert error.context.get("input") == input
    assert (
        error.message() == f"1XX: Only one 1XX tag is allowed. Record contains: {input}"
    )
    assert (
        error.message_template
        == "1XX: Only one 1XX tag is allowed. Record contains: {input}"
    )
    assert error.error_details.get("loc") == input
    assert error.error_details.get("input") == input


def test_missing_required_field():
    error = MissingRequiredField({"input": "245"})
    assert error.type == "missing_required_field"
    assert error.context.get("input") == "245"
    assert error.message() == "One 245 field must be present in a MARC21 record."
    assert (
        error.message_template
        == "One {input} field must be present in a MARC21 record."
    )
    assert error.error_details.get("loc") == ("245",)
    assert error.error_details.get("input") == "245"


def test_non_repeatable_field():
    error = NonRepeatableField({"input": "100", "loc": "100"})
    assert error.type == "non_repeatable_field"
    assert error.context.get("input") == "100"
    assert error.message() == "100: Has been marked as a non-repeating field."
    assert (
        error.message_template == "{input}: Has been marked as a non-repeating field."
    )
    assert error.error_details.get("loc") == ("100",)
    assert error.error_details.get("input") == "100"


@pytest.mark.parametrize(
    "tag, code, subfields",
    [
        (
            "300",
            "b",
            [
                PymarcSubfield(code="b", value="foo"),
                PymarcSubfield(code="b", value="bar"),
            ],
        ),
        (
            "010",
            "a",
            [
                PymarcSubfield(code="a", value="foo"),
                PymarcSubfield(code="a", value="bar"),
            ],
        ),
    ],
)
def test_non_repeatable_subfield(tag, code, subfields):
    invalid_subfields = [i for i in subfields if i.code == code]
    error = NonRepeatableSubfield({"loc": (tag, code), "input": invalid_subfields})
    assert error.type == "non_repeatable_subfield"
    assert error.context.get("tag") == tag
    assert error.message() == f"{tag} ${code}: Subfield cannot repeat."
    assert error.message_template == "{tag} ${code}: Subfield cannot repeat."
    assert error.error_details.get("loc") == (tag, code)
    assert error.error_details.get("input") == subfields
