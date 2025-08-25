"""
Utility functions for MARC record validation.

This module provides helper functions used during the validation of MARC records,
specifically for handling validation rules and validation errors in a structured
way.

Functions:

add_rules_to_pymarc_fields:
    Adds rule metadata from a `RuleSet` to MARC fields.

handle_errors:
    Wraps validators to capture and normalize Pydantic validation errors.
raise_validation_errors:
    Raises a `ValidationError` from a list of error details.
"""

from __future__ import annotations

from typing import Any, Callable, List

from pydantic import ValidationError, ValidationInfo
from pydantic_core import InitErrorDetails

from pydantic_marc.errors import MarcCustomError
from pydantic_marc.marc_rules import RuleSet


def add_rules_to_pymarc_fields(data: List[Any], info: ValidationInfo) -> List[Any]:
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
    rule_set = RuleSet.from_validation_info(info=info)
    rules = rule_set.rules if rule_set else {}
    field_list = []

    for field in data:
        rule = rules.get(field.tag, None)
        field_dict = {"rules": rule, "tag": field.tag}
        if getattr(field, "control_field") is True:
            field_dict["data"] = field.data
        else:
            field_dict["indicators"] = field.indicators
            field_dict["subfields"] = field.subfields
        if field.tag == "007":
            rule_dict = field_dict["rules"].__dict__
            material_types = field_dict["rules"].model_extra["material_types"]
            rule_dict["length"] = material_types[field_dict["data"][0]]["length"]
            rule_dict["values"] = material_types[field_dict["data"][0]]["values"]
            field_dict["rules"] = rule_dict
        field_list.append(field_dict)
    return field_list


def handle_errors(
    validator: Callable, data: Any, info: ValidationInfo
) -> tuple[Any, List[InitErrorDetails]]:
    """
    Execute a validator function and convert any errors raised to custom errors.

    This function wraps the execution of a validator, catching `ValidationError`
    exceptions and converting each error into a `MarcCustomError`. It returns the
    original or validated data along with a list of `InitErrorDetails` used for raising
    or aggregating errors later.

    Args:
        validator: a callable validator function that takes `data` and `info`.
        data: the input data as a list to be validated.
        info: the `ValidationInfo` used during model validation.

    Returns:
        a tuple containing the validated data (or original data if invalid), and a
        list of Pydantic-compatible error details.
    """
    try:
        return validator(data, info), []
    except ValidationError as exc:
        errors = [MarcCustomError(e["type"], e["msg"], e["ctx"]) for e in exc.errors()]
        return data, [i.error_details for i in errors]


def marc_field_validator(error_checker_func: Callable) -> Callable:
    """
    Wrapper function to run field-level validation for a MARC field using
    rules from the model.

    This function looks up a validation function based on the field name and applies
    it if a corresponding rule and validator are found. If no rule or validator is
    found, the input `data` is returned unchanged. If validation errors are found,
    they are raised using `raise_validation_errors`.

    Args:
        data: the data passed to the field being validated
        info: A `ValidationInfo` object.

    Returns:
        The validated field data, or raises a `ValidationError` if rules are violated.
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(data: Any, info: ValidationInfo) -> Any:
            rule = info.data.get("rules", None)
            if not rule:
                return data
            errors = error_checker_func(rule=rule, data=data, tag=info.data["tag"])
            return raise_validation_errors(errors=errors, data=data)

        return wrapper

    return decorator


def raise_validation_errors(errors: List[InitErrorDetails], data: Any) -> Any:
    """
    Raise a `ValidationError` if any collected error details exist.

    This function takes a list of Pydantic `InitErrorDetails` objects and raises a
    `ValidationError` if the list is not empty. Otherwise, it returns the validated
    data.

    Args:
        errors: a list of error details to raise, if any.
        data: the data object being validated (used to name the error context).

    Returns:
        The input data, validated, if no errors were raised.

    Raises:
        `ValidationError` from the collected `errors`.
    """
    if errors:
        raise ValidationError.from_exception_data(
            title=data.__class__.__name__, line_errors=errors
        )
    return data
