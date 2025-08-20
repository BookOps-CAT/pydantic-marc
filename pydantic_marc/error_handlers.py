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

from collections import Counter
from typing import Any, List

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
from pydantic_marc.marc_rules import Rule, RuleSet


def get_control_field_errors(rule: Rule, data: Any, tag: str) -> List[InitErrorDetails]:
    """
    Validate the length of a control field's `data` string against the expected rule.

    If the `data` string length does not match the expected length specified in
    the rule, a `ControlFieldLength` error is returned. If a character does not match
    the expected value at a specific position, an `InvalidFixedField` error is returned.

    Args:
        rule: the `Rule` object defining the expected length and values for the field.
        data: data passed to the `ControlField.data` attribute.
        tag: the MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: List[InitErrorDetails] = []
    valid_length = rule.length
    if not valid_length:
        return errors
    match = len(data) == valid_length
    if match is False:
        error = ControlFieldLength({"tag": tag, "valid": valid_length, "input": data})
        errors.append(error.error_details)
        return errors
    value_rules = rule.values
    if value_rules:
        for i, char in enumerate(data):
            values = value_rules[f"{i:02d}"]
            if char not in values:
                error_data = {
                    "tag": tag,
                    "input": char,
                    "valid": values,
                    "loc": f"{i:02d}",
                }
                errors.append(InvalidFixedField(error_data).error_details)
    return errors


def get_indicator_errors(rule: Rule, data: Any, tag: str) -> List[InitErrorDetails]:
    """
    Validate the indicator values of a `DataField` against the allowed values in a rule.

    Each indicator is checked against the corresponding `ind1` or `ind2` list in the rule.
    If an indicator is invalid, an `InvalidIndicator` error is returned.

    Args:
        rule: the `Rule` object defining the expected length for the field.
        data: data passed to the `DataField.indicators` attribute.
        tag: the MARC field tag being validated.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: List[InitErrorDetails] = []
    for n, indicator in enumerate(data):
        ind = f"ind{n + 1}"
        valid_inds = getattr(rule, ind)
        if data[n] not in valid_inds:
            error_data = {"loc": (tag, ind), "input": indicator, "valid": valid_inds}
            errors.append(InvalidIndicator(error_data).error_details)
    return errors


def get_subfield_errors(rule: Rule, data: Any, tag: str) -> List[InitErrorDetails]:
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
    errors: List[InitErrorDetails] = []
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
    data: List[Any], info: ValidationInfo
) -> List[InitErrorDetails]:
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
    errors: List[InitErrorDetails] = []
    rules = RuleSet.from_validation_info(info=info)
    if not rules:
        return errors
    tag_counts = Counter([i["tag"] for i in data])
    nr_fields = [k for k, v in rules.rules.items() if v.repeatable is False]
    required_fields = [k for k, v in rules.rules.items() if v.required is True]
    main_entries = [i for i in tag_counts.elements() if i.startswith("1")]

    for tag in nr_fields:
        if tag_counts[tag] > 1:
            errors.append(NonRepeatableField({"input": tag}).error_details)
    for tag in required_fields:
        if tag not in tag_counts.elements():
            errors.append(MissingRequiredField({"input": tag}).error_details)
    if len(main_entries) > 1:
        errors.append(MultipleMainEntryValues({"input": main_entries}).error_details)
    return errors


def get_leader_errors(data: Any, info: ValidationInfo) -> List[InitErrorDetails]:
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
    errors: list = []
    rules = info.data["rules"]
    if not rules or not rules.rules:
        return errors
    rule = rules.rules.get("LDR")
    if not rule or not rule.values:
        return errors
    data = str(data)
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
