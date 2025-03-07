"""Custom validators for `ControlField`, `DataField`, and `MarcRecord` models.

The functions contained within this module validate the content of the data passed to
`ControlField`, `DataField` and `MarcRecord` models. They are used as before, after,
or wrap validators.
"""

from collections import Counter
from typing import Any, Dict, List, Optional

from pydantic import ValidationError, ValidationInfo, ValidatorFunctionWrapHandler
from pymarc import Field as PymarcField

from pydantic_marc.errors import (
    ControlFieldLength,
    InvalidIndicator,
    InvalidSubfield,
    MarcCustomError,
    MissingRequiredField,
    MultipleMainEntryValues,
    NonRepeatableField,
    NonRepeatableSubfield,
)


def check_marc_rules(fields: List[Any], info: ValidationInfo) -> List[Dict[str, Any]]:
    """
    Identify the rules to validate a field's content against before validating a
    MarcRecord object. This function is a BeforeValidator for the MarcRecord.fields
    attribute.

    The function identifies which rules to use by checking three different places for
    MARC rules. It first checks if MARC rules were passed to the model via validation
    context (indentified in the `ValidationInfo.context` attribute) and then checks if
    rules were passed directly to the model via the `MarcRecord.rules` attribute. The
    function then checks if each field within the `MarcRecord.fields` has been passed
    separate rules. If the field was passed rules directly, then the model will validate
    against those rules. If not, then the function passes the rules from the parent
    `RecordModel` to the child `DataField` or `ControlField` model.

    Args:

        fields: a list of objects passed to the `MarcRecord.fields` attribute
        info: a `ValidationInfo` object

    Returns:

        a list of dictionaries representing the fields within the MarcRecord
    """
    if info.context is not None and "rules" in info.context:
        rules = info.context.get("rules", info.data.get("rules"))
    else:
        rules = info.data.get("rules")
    field_list = []
    for field in fields:
        tag = field.get("tag") if isinstance(field, dict) else field.tag
        if isinstance(field, dict) and field.get("rules") is None:
            field["rules"] = {tag: rules.get(field["tag"], {})}
        elif hasattr(field, "rules") and "rules" not in field.model_fields_set:
            field.rules = {tag: rules.get(tag, {})}
        elif isinstance(field, PymarcField) and field.is_control_field():
            field = {"rules": {tag: rules.get(tag, {})}, "tag": tag, "data": field.data}
        elif isinstance(field, PymarcField) and not field.is_control_field():
            field = {
                "rules": {tag: rules.get(tag, {})},
                "tag": tag,
                "indicators": field.indicators,
                "subfields": field.subfields,
            }
        field_list.append(field)
    return field_list


def validate_control_field(data: str, info: ValidationInfo) -> str:
    """
    Confirm that the `data` attribute of a `ControlField` object matches the rules
    defined for that field. This currently matches the length of the field against the
    rule as defined in the `rules.py` module. If the length of the string passed to the
    `data` attribute does not match the rules for that field, a `ControlFieldLength`
    error will be raised.


    Args:

        data: string passed to the `ControlField.data` attribute
        info: a `ValidationInfo` object

    Returns:

        a string representing the representing the validated `data` attribute
    """
    tag = info.data["tag"]
    field_rules = info.data["rules"].get(tag, {})
    length = field_rules.get("length")

    if not length:
        return data

    if tag == "007":
        length = field_rules["length"].get(data[0])

    if isinstance(length, list):
        match = any(len(data) == i for i in length)
    else:
        match = len(data) == length
    if match is False:
        error = ControlFieldLength({"tag": tag, "valid": length, "input": data})
        raise ValidationError.from_exception_data(
            title=data.__class__.__name__, line_errors=[error.error_details]
        )
    return data


def validate_indicators(indicators: tuple, info: ValidationInfo) -> tuple:
    """
    Confirm that the values passed to the `indicators` attribute of a `DataField` object
    match the rules defined for that field as defined in the `rules.py` module. If the
    values do not match the rules for that field, an `InvalidIndicator` error will be
    raised.

    Args:

        indicators: a tuple passed to the `DataField.indicators` attribute
        info: a `ValidationInfo` object

    Returns:

        a tuple representing the validated `indicators` attribute
    """
    tag = info.data["tag"]
    field_rules = info.data["rules"].get(tag, None)

    if not field_rules:
        return indicators
    errors = []
    for n, indicator in enumerate(indicators):
        ind = f"ind{n+1}"
        valid = field_rules.get(ind)
        if indicator not in valid:
            error = InvalidIndicator(
                {"loc": (tag, ind), "input": indicators[n], "valid": valid}
            )
            errors.append(error.error_details)
    if errors:
        raise ValidationError.from_exception_data(
            title=indicators.__class__.__name__, line_errors=errors
        )
    return indicators


def validate_fields(
    fields: List[Any], handler: ValidatorFunctionWrapHandler, info: ValidationInfo
) -> Optional[List[Any]]:
    """
    Confirm that the values passed to the `fields` attribute of a `MarcRecord` object
    match the rules defined for that field as defined in the `rules.py` module. If the
    values do not match the rules for that field, a `NonRepeatableField` error, a
    MissingRequiredField error and/or a `MultipleMainEntryValues` error will be raised.

    This is a `WrapValidator` on the `fields` field meaning that it will collect all
    errors raised in any nested models and raise them at the same time as it raises any
    errors identified while validating the parent model.

    Args:

        fields: a list of objects passed to the `MarcRecord.fields` attribute
        info: a `ValidationInfo` object

    Returns:

        a list representing the validated `fields` attribute
    """

    errors = []

    fields = check_marc_rules(fields=fields, info=info)

    try:
        validate_marc_fields(fields=fields, info=info)
    except ValidationError as exc:
        errors.extend(exc.errors())

    validated_fields = None
    try:
        validated_fields = handler(fields)
    except ValidationError as exc:
        errors.extend(exc.errors())

    if errors:
        line_errors = []
        title = fields.__class__.__name__
        for e in errors:
            marc_error = MarcCustomError(e["type"], e["msg"], e["ctx"])
            line_errors.append(marc_error.error_details)
        raise ValidationError.from_exception_data(title=title, line_errors=line_errors)
    return validated_fields


def validate_marc_fields(fields: Any, info: ValidationInfo) -> Optional[List[Any]]:
    """
    Confirm that the values passed to the `fields` attribute of a `MarcRecord` object
    match the rules defined for that field as defined in the `rules.py` module. If the
    values do not match the rules for that field, a `NonRepeatableField` error, a
    MissingRequiredField error and/or a `MultipleMainEntryValues` error will be raised.

    This is a `WrapValidator` on the `fields` field meaning that it will collect all
    errors raised in any nested models and raise them at the same time as it raises any
    errors identified while validating the parent model.

    Args:

        fields: a list of objects passed to the `MarcRecord.fields` attribute
        info: a `ValidationInfo` object

    Returns:

        a list representing the validated `fields` attribute
    """
    errors = []

    rules = info.data["rules"]
    tag_list = [i["tag"] for i in fields]
    tag_counts = Counter(tag_list)

    nr_fields = [k for k, v in rules.items() if v.get("repeatable") is False]
    for tag in set(tag_list):
        if tag_counts[tag] > 1 and tag in nr_fields:
            nr_error = NonRepeatableField({"input": tag})
            errors.append(nr_error.error_details)
    required_fields = [k for k, v in rules.items() if v.get("required") is True]
    for tag in required_fields:
        if tag not in tag_list:
            missing_error = MissingRequiredField({"input": tag})
            errors.append(missing_error.error_details)
    main_entries = [i for i in tag_counts.elements() if i.startswith("1")]
    if len(main_entries) > 1:
        multiple_error = MultipleMainEntryValues({"input": main_entries})
        errors.append(multiple_error.error_details)
    if errors:
        raise ValidationError.from_exception_data(
            title=fields.__class__.__name__, line_errors=errors
        )
    return fields


def validate_subfields(subfields: List[Any], info: ValidationInfo) -> List[Any]:
    """
    Confirm that the values passed to the `subfields` attribute of a `DataField` object
    match the rules defined for that field as defined in the `rules.py` module. If the
    values do not match the rules for that field, a `NonRepeatableSubfield` error and/or
    an `InvalidSubfield` error will be raised.

    Args:

        subfields: a list of objects passed to the `DataField.subfields` attribute
        info: a `ValidationInfo` object

    Returns:

        a list representing the validated `subfields` attribute
    """
    tag = info.data["tag"]
    field_rules = info.data["rules"].get(tag, None)

    if not field_rules:
        return subfields

    errors = []
    valid_subfields = field_rules["subfields"].get("valid", [])
    nr_subfields = field_rules["subfields"].get("non_repeatable", [])

    all_codes: Counter = Counter()
    for sub in subfields:
        all_codes += Counter(list(sub.code))

    subfield_codes = set(all_codes.elements())

    invalid_nr_fields = [
        i for i in subfield_codes if i in nr_subfields and all_codes[i] > 1
    ]
    for code in invalid_nr_fields:
        input = [i for i in subfields if i.code == code]
        nr_error = NonRepeatableSubfield({"loc": (tag, code), "input": input})
        errors.append(nr_error.error_details)
    invalid_subfields = [
        i for i in subfield_codes if valid_subfields and i not in valid_subfields
    ]
    for code in invalid_subfields:
        input = [i for i in subfields if i.code == code]
        invalid_sub_error = InvalidSubfield({"loc": (tag, code), "input": input})
        errors.append(invalid_sub_error.error_details)
    if errors:
        raise ValidationError.from_exception_data(
            title=subfields.__class__.__name__, line_errors=errors
        )
    return subfields
