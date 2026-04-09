"""Custom validation functions for `MarcRecord` models.

The validator functions in this module are used as either before or wrap validators
depending on the field and model.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from pydantic import ValidationInfo

from .error_handlers import ErrorCollector, MarcValidator, ValidationHandler
from .errors import (
    MarcCustomError,
    MissingRequiredField,
    MultipleMainEntryValues,
    NonRepeatableField,
)


def add_rules_to_pymarc_fields(data: list[Any], info: ValidationInfo) -> list[Any]:
    """
    Add rules to each MARC field in a record.

    This function creates a `RuleSet` from the provided `ValidationInfo` and uses it
    to add each field in the `data` list with the appropriate `Rule` based on the
    field's tag. The function constructs a list of dicts representing the fields,
    each enriched with its tag, rule, and either control field data or
    indicators/subfields.

    Args:
        data:
            a list of `pymarc.Field` objects or similarly structured data.
            The data is assumed to contain `tag`, and `control_field` attributes
            and, depending on the field, `indicators`, `subfields`, and/or `data`
            attributes.
        info:
            the `ValidationInfo` object provided during model validation.

    Returns:
        a list of dictionaries where each item represents a MARC field and its
        associated `Rule`.
    """
    rule_set = info.data["rules"]
    rules = rule_set.rules if rule_set else {}
    field_list = []

    for field in data:
        rule = rules.get(field.tag, None)
        if field.tag == "007" and rule:
            rule = rule.get(field.data[0], {})
        field_dict = {"rules": rule, "tag": field.tag}
        if getattr(field, "control_field", field.is_control_field()) is True:
            field_dict["data"] = field.data
        else:
            field_dict["indicators"] = field.indicators
            field_dict["subfields"] = field.subfields
        field_list.append(field_dict)
    return field_list


def get_marc_field_errors(
    data: list[Any], info: ValidationInfo
) -> list[MarcCustomError]:
    """
    Validate rules across all fields in a `MarcRecord`.

    Confirm that the values passed to the `MarcRecord.fields` attribute conform to the
    rules passed to the `MarcRecord.rules` attribute. If the values do not match the
    rules for that field, a `NonRepeatableField` error, a `MissingRequiredField`
    error and/or a `MultipleMainEntryValues` error will be raised.

    This is a part of the `WrapValidator` on the `fields` field and when called by the
    `MarcValidator` class and runs before validating the model. This means that it will
    collect all errors raised within this function and then raise them at the same it
    raises any errors identified while validating the parent model.

    This includes:
    - Checking that non-repeatable fields appear no more than once.
    - Confirming that required fields are present.
    - Ensuring that only one main entry field (1XX tag) exists.

    Args:
        data: A list of fields from a `MarcRecord`.
        info: A `ValidationInfo` context used to extract applicable rules.

    Returns:

        A list of `MarcCustomError` objects.
    """
    errors: list[MarcCustomError] = []
    rules = info.data["rules"]
    if not rules:
        return errors
    tag_counts = Counter([i["tag"] for i in data])
    main_entries = [i for i in tag_counts.elements() if i.startswith("1")]

    for tag in rules.non_repeatable_fields:
        if tag_counts[tag] > 1:
            errors.append(NonRepeatableField({"input": tag}))
    for tag in rules.required_fields:
        if tag not in tag_counts.elements():
            errors.append(MissingRequiredField({"input": tag}))
    if len(main_entries) > 1:
        errors.append(MultipleMainEntryValues({"input": main_entries}))
    return errors


def validate_marc_fields(data: Any, handler: Callable, info: ValidationInfo) -> Any:
    """
    Confirm that the values passed to the `MarcRecord.fields` attribute conforms to the
    defined for the record. If the values do not match the rules for
    the record, a `NonRepeatableField` error, a `MissingRequiredField` error and/or a
    `MultipleMainEntryValues` error will be raised.


    This function is called before validation of the `MarcRecord` model within the
    `WrapValidator` on the `MarcRecord.fields` attribute.

    Args:

        data: A list of objects passed to the `MarcRecord.fields` attribute.
        info: A `ValidationInfo` object.

    Returns:

        A list representing the validated `fields` attribute.

    Raises:
        `ValidationError`: if the there are any MARC validation errors
    """
    # Running BeforeValidator for `MarcRecord`
    all_errors = []

    collector = ErrorCollector()
    data = add_rules_to_pymarc_fields(data=data, info=info)
    data, errors = collector.collect_errors(
        data=data, info=info, validator=MarcValidator(get_marc_field_errors)
    )
    all_errors.extend(errors)

    # Validating `MarcRecord`
    data, errors = collector.collect_errors(data=data, info=info, validator=handler)
    all_errors.extend(errors)

    return ValidationHandler().raise_if_errors(errors=all_errors, data=data)
