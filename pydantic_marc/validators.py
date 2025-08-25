"""Custom validation functions for `ControlField`, `DataField`, and `MarcRecord` models.

The validator functions in this module are used as either after or wrap validators
depending on the field and model.
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import ValidationInfo

from pydantic_marc.error_handlers import (
    get_control_field_length_errors,
    get_control_field_value_errors,
    get_indicator_errors,
    get_leader_errors,
    get_marc_field_errors,
    get_subfield_errors,
)
from pydantic_marc.utils import (
    add_rules_to_pymarc_fields,
    handle_errors,
    marc_field_validator,
    raise_validation_errors,
)


@marc_field_validator(get_control_field_length_errors)
def validate_length(data: Any, info: ValidationInfo) -> None: ...


@marc_field_validator(get_control_field_value_errors)
def validate_values(data: Any, info: ValidationInfo) -> None: ...


@marc_field_validator(get_indicator_errors)
def validate_indicators(data: Any, info: ValidationInfo) -> None: ...


@marc_field_validator(get_subfield_errors)
def validate_subfields(data: Any, info: ValidationInfo) -> None: ...


def validate_marc_data(data: Any, info: ValidationInfo) -> Any:
    """
    Confirm that the values passed to the `MarcRecord.fields` attribute conform to the
    rules passed to the `MarcRecord.rules` attribute. If the values do not match the
    rules for that field, a `NonRepeatableField` error, a `MissingRequiredField`
    error and/or a `MultipleMainEntryValues` error will be raised.

    This is a part of the `WrapValidator` on the `fields` field and runs before
    validating the model. This means that it will collect all errors raised within this
    function and then raise them at the same it raises any errors identified while
    validating the parent model.

    Args:

        data: The input data passed to the `MarcRecord.fields` attribute.
        info: A `ValidationInfo` object.

    Returns:

        A list of `MarcCustomError` objects.


    Raises:
        `ValidationError` if the there are any MARC validation errors
    """
    errors = get_marc_field_errors(data=data, info=info)
    return raise_validation_errors(errors, data=data)


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
        `ValidationError` if the there are any MARC validation errors
    """
    # Running BeforeValidator for `MarcRecord`
    all_errors = []

    data = add_rules_to_pymarc_fields(data=data, info=info)
    data, errors = handle_errors(data=data, info=info, validator=validate_marc_data)
    all_errors.extend(errors)

    # Validating `MarcRecord`
    data, errors = handle_errors(data=data, info=info, validator=handler)
    all_errors.extend(errors)

    return raise_validation_errors(errors=all_errors, data=data)


def validate_leader(data: Any, info: ValidationInfo) -> Any:
    """
    Confirm that the value passed to the `MarcRecord.leader` attribute conforms to the
    rules passed to the `MarcRecord.rules` attribute. If the values do not match the
    rules for that field, one or more `InvalidLeader` errors will be raised.

    This is a the `BeforeValidator` on the `leader` field and runs before validating
    the model. These errors will be collected and raised with any other errors
    identified while validating the `MarcRecord`.

    Args:

        data: The input data passed to the `MarcRecord.leader` attribute.
        info: A `ValidationInfo` object.

    Returns:

        A list of `MarcCustomError` objects.


    Raises:
        `ValidationError` if the there are any MARC validation errors
    """
    errors = get_leader_errors(data=str(data), info=info)
    return raise_validation_errors(errors=errors, data=str(data))
