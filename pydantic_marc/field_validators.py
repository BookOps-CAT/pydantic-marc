"""Custom validation functions for `ControlField`, `DataField`, and `MarcRecord` models.

The validator functions in this module are used as either after or wrap validators
depending on the field and model.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Sequence, Union

from .constants import COUNTRY_CODES, LANGUAGE_CODES
from .errors import (
    ControlFieldLength,
    InvalidFixedField,
    InvalidIndicator,
    InvalidLeader,
    InvalidSubfield,
    MarcCustomError,
    NonRepeatableSubfield,
)

if TYPE_CHECKING:  # pragma: no cover
    from .components import PydanticIndicators, PydanticSubfield
    from .marc_rules import Rule


def get_control_field_length_errors(
    rule: Rule, data: str, tag: str
) -> list[MarcCustomError]:
    """
    Validate the length of a control field's `data` string against the expected rule.

    If the `data` string length does not match the expected length specified in
    the rule, a `ControlFieldLength` error is returned.

    Args:
        rule: the `Rule` object defining the expected length and values for the field.
        data: data passed to the `ControlField.data` attribute.
        tag: the MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    valid_length = rule.length
    if not valid_length:
        return errors
    match = len(data) == valid_length
    if match is False:
        error = ControlFieldLength({"tag": tag, "valid": valid_length, "input": data})
        errors.append(error)
    return errors


def get_control_field_value_errors(
    rule: Rule, data: str, tag: str
) -> list[MarcCustomError]:
    """
    Validate the values of each character of a control field's `data` string
    against the expected rule.

    If a character does not match the expected value at a specific position,
    an `InvalidFixedField` error is returned. The values are validated after
    the length of the `ControlField` has been validated in order
    to avoid misleading error messages due to missing or extra values.

    Args:
        rule: the `Rule` object defining the expected length and values for the field.
        data: data passed to the `ControlField.data` attribute.
        tag: the MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    value_rules = rule.field_values
    if value_rules:
        data_dict = {f"{i:02d}": char for i, char in enumerate(data)}
        for position in value_rules.keys():
            if "-" in position:
                start, end = position.split("-")
                keys_in_range = [f"{i:02d}" for i in range(int(start), int(end) + 1)]
                data_dict[position] = "".join([data_dict[i] for i in keys_in_range])
                for pos in range(int(start), int(end) + 1):
                    data_dict.pop(f"{pos:02d}")
        for loc, char in data_dict.items():
            values = value_rules.get(loc)
            if values and char not in values:
                error_data = {"tag": tag, "input": char, "valid": values, "loc": loc}
                errors.append(InvalidFixedField(error_data))
    if tag == "008":
        lang = data[35:38]
        country = data[15:18]
        if lang not in LANGUAGE_CODES:
            error_data = {
                "tag": tag,
                "input": lang,
                "valid": "see https://id.loc.gov/vocabulary/languages.html for "
                "list of valid language codes",
                "loc": "35-37",
            }
            errors.append(InvalidFixedField(error_data))
        if country not in COUNTRY_CODES:
            error_data = {
                "tag": tag,
                "input": country,
                "valid": "see https://id.loc.gov/vocabulary/countries.html for "
                "list of valid country codes",
                "loc": "15-17",
            }
            errors.append(InvalidFixedField(error_data))

    return errors


def get_indicator_errors(
    rule: Rule, data: Union[PydanticIndicators, Sequence], tag: str
) -> list[MarcCustomError]:
    """
    Validate the indicator values of a `DataField` against the allowed values in a rule.

    Each indicator is checked against the corresponding `ind1` or `ind2` list in the
    rule. If an indicator is invalid, an `InvalidIndicator` error is returned.

    Args:
        rule: the `Rule` object defining the expected length for the field.
        data: data passed to the `DataField.indicators` attribute.
        tag: the MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    for n, indicator in enumerate(data):
        ind = f"ind{n + 1}"
        valid_inds = getattr(rule, ind, "")
        if data[n] not in valid_inds:
            error_data = {"loc": (tag, ind), "input": indicator, "valid": valid_inds}
            errors.append(InvalidIndicator(error_data))
    return errors


def get_leader_errors(rule: Rule, data: str, tag: str) -> list[MarcCustomError]:
    """
    Validate each character in a string against the allowed values each byte in a
    MARC leader.

    If the value does not match the rules for the leader, an `InvalidLeader`
    error will be added to the list of errors and returned.

    Args:
        rule: The `Rule` object specifying the valid leader values.
        data: A string passed to the `MarcRecord.leader` attribute.
        tag: The MARC field tag being validated ('LDR').
    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    values = rule.field_values
    if not values:
        return errors
    for i, c in enumerate(data):
        position = str(i).zfill(2)
        print(values)
        valid = values.get(f"{position}", [])
        if c not in valid:
            error_data = {"input": c, "loc": f"{position}", "valid": valid, "tag": tag}
            errors.append(InvalidLeader(error_data))
    return errors


def get_subfield_errors(
    rule: Rule, data: list[PydanticSubfield], tag: str
) -> list[MarcCustomError]:
    """
    Validate the subfields in a `DataField` against the allowed and repeatable values
    in a rule.

    This function checks two rule-based constraints:
    - Whether a subfield appears more than once when marked as non-repeatable.
    - Whether a subfield is not listed in the valid subfield codes.

    If the values do not match the rules for the field, a `NonRepeatableSubfield`
    error and/or an `InvalidSubfield` error will be added to the list of errors and
    returned.

    Args:
        rule: The `Rule` object specifying valid and repeatable subfields.
        data: A list of `PydanticSubfield` instances from the `DataField`.
        tag: The MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    sub_rules = rule.subfields
    if not sub_rules:
        return errors

    sub_codes: Counter = Counter([sub.code for sub in data])
    deduped_sub_codes = set(sub_codes.elements())

    valid_sub_codes = sub_rules.get("valid", [])
    nr_sub_codes = sub_rules.get("non_repeatable", [])

    for code in deduped_sub_codes:
        error_data = {"loc": (tag, code), "input": [i for i in data if i.code == code]}
        if sub_codes[code] > 1 and code in nr_sub_codes:
            errors.append(NonRepeatableSubfield(error_data))
        elif valid_sub_codes and code not in valid_sub_codes:
            errors.append(InvalidSubfield(error_data))
    return errors
