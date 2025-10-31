"""
Error handling functions for MARC field validation.

This module defines specialized error-checking logic for different components of
a MARC record (ie. `ControlField.data`, `DataField.indicators`, `DataField.subfields`,
`MarcRecord.fields`). Each function evaluates its input against a set of rules
defined in a `Rule` or `RuleSet` and returns a list of structured error details if
any violations are found.

Functions in this module are invoked by custom validators during model validation
and return lists of `InitErrorDetails` objects to support Pydantic-compatible error
reporting.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Sequence, Union

from pydantic import ValidationInfo
from pydantic_core import InitErrorDetails

from pydantic_marc.errors import (
    ControlFieldLength,
    InvalidFixedField,
    InvalidIndicator,
    InvalidLeader,
    InvalidSubfield,
    MissingRequiredField,
    MultipleMainEntryValues,
    NonRepeatableField,
    NonRepeatableSubfield,
)
from pydantic_marc.marc_rules import RuleSet

if TYPE_CHECKING:  # pragma: no cover
    from pydantic_marc.fields import PydanticIndicators, PydanticSubfield
    from pydantic_marc.marc_rules import Rule


@lru_cache
def marc_codes() -> dict[str, Any]:
    rules = {}
    base_dir = os.path.dirname(__file__)
    json_path = os.path.join(base_dir, "validation_rules", "marc_codes.json")
    with open(json_path, "r", encoding="utf-8") as fh:
        rules.update({k: v for k, v in json.load(fh).items()})
    return rules


def get_control_field_value_errors(
    rule: Rule, data: str, tag: str
) -> list[InitErrorDetails]:
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
    errors: list[InitErrorDetails] = []
    value_rules = rule.values
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
                errors.append(InvalidFixedField(error_data).error_details)
    if tag == "008":
        codes = marc_codes()
        if data[35:38] not in codes["language_codes"].keys():
            error_data = {
                "tag": tag,
                "input": data[35:38],
                "valid": "see https://id.loc.gov/vocabulary/languages.html for "
                "list of valid language codes",
                "loc": "35-37",
            }
            errors.append(InvalidFixedField(error_data).error_details)
        country_codes = [f"{i.ljust(3, ' ')}" for i in codes["country_codes"].keys()]
        if data[15:18] not in country_codes:
            error_data = {
                "tag": tag,
                "input": data[15:18],
                "valid": "see https://id.loc.gov/vocabulary/countries.html for "
                "list of valid country codes",
                "loc": "15-17",
            }
            errors.append(InvalidFixedField(error_data).error_details)

    return errors


def get_control_field_length_errors(
    rule: Rule, data: str, tag: str
) -> list[InitErrorDetails]:
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
    errors: list[InitErrorDetails] = []
    valid_length = rule.length
    if not valid_length:
        return errors
    match = len(data) == valid_length
    if match is False:
        error = ControlFieldLength({"tag": tag, "valid": valid_length, "input": data})
        errors.append(error.error_details)
    return errors


def get_indicator_errors(
    rule: Rule, data: Union[PydanticIndicators, Sequence], tag: str
) -> list[InitErrorDetails]:
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
    errors: list[InitErrorDetails] = []
    for n, indicator in enumerate(data):
        ind = f"ind{n + 1}"
        valid_inds = getattr(rule, ind)
        if data[n] not in valid_inds:
            error_data = {"loc": (tag, ind), "input": indicator, "valid": valid_inds}
            errors.append(InvalidIndicator(error_data).error_details)
    return errors


def get_subfield_errors(
    rule: Rule, data: list[PydanticSubfield], tag: str
) -> list[InitErrorDetails]:
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
    errors: list[InitErrorDetails] = []
    if not rule.subfields:
        return errors

    sub_codes: Counter = Counter([sub.code for sub in data])
    deduped_sub_codes = set(sub_codes.elements())

    valid_sub_codes = rule.subfields.get("valid", [])
    nr_sub_codes = rule.subfields.get("non_repeatable", [])

    for code in deduped_sub_codes:
        error_data = {"loc": (tag, code), "input": [i for i in data if i.code == code]}
        if sub_codes[code] > 1 and code in nr_sub_codes:
            errors.append(NonRepeatableSubfield(error_data).error_details)
        elif valid_sub_codes and code not in valid_sub_codes:
            errors.append(InvalidSubfield(error_data).error_details)
    return errors


def get_marc_field_errors(
    data: list[Any], info: ValidationInfo
) -> list[InitErrorDetails]:
    """
    Validate rules across all fields in a `MarcRecord`.

    This includes:
    - Checking that non-repeatable fields appear no more than once.
    - Confirming that required fields are present.
    - Ensuring that only one main entry field (1XX tag) exists.

    This function is called before validation of the `MarcRecord` model within the
    `WrapValidator` on the `MarcRecord.fields` attribute.

    Args:
        data: A list of fields from a `MarcRecord`.
        info: A `ValidationInfo` context used to extract applicable rules.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[InitErrorDetails] = []
    rules = RuleSet.from_validation_info(info=info)
    if not rules:
        return errors
    tag_counts = Counter([i["tag"] for i in data])
    main_entries = [i for i in tag_counts.elements() if i.startswith("1")]

    for tag in rules.non_repeatable_fields:
        if tag_counts[tag] > 1:
            errors.append(NonRepeatableField({"input": tag}).error_details)
    for tag in rules.required_fields:
        if tag not in tag_counts.elements():
            errors.append(MissingRequiredField({"input": tag}).error_details)
    if len(main_entries) > 1:
        errors.append(MultipleMainEntryValues({"input": main_entries}).error_details)
    return errors


def get_leader_errors(data: str, info: ValidationInfo) -> list[InitErrorDetails]:
    """
    Validate each character in a string against the allowed values each byte in a
    MARC leader.

    If the value does not match the rules for the leader, an `InvalidLeader`
    error will be added to the list of errors and returned.

    Args:
        data: A string passed to the `MarcRecord.leader` attribute.
        info: A `ValidationInfo` context used to extract applicable rules.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[InitErrorDetails] = []
    rules = info.data["rules"]
    if not rules or not rules.rules:
        return errors
    rule = rules.rules.get("LDR")
    if not rule or not rule.values:
        return errors
    for i, c in enumerate(data):
        position = str(i).zfill(2)
        valid = rule.values.get(f"{position}", [])
        if c not in valid:
            errors.append(
                InvalidLeader(
                    {"input": c, "loc": f"{position}", "valid": valid}
                ).error_details
            )
    return errors
