"""Models that define fields within MARC record objects.

Models defined in this module include:

`ControlField`:
    a model to validate MARC 00x fields. Contains `tag` and `data` attributes.
`DataField`:
    a model to validate all other MARC fields. Contains `tag`, `indicators`
    and `subfield` attributes.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Sequence, Union

from pydantic import AfterValidator, BaseModel, Field, ValidationInfo, model_serializer

from .components import PydanticIndicators, PydanticSubfield
from .field_validators import (
    get_control_field_length_errors,
    get_control_field_value_errors,
    get_indicator_errors,
    get_subfield_errors,
    marc_field_validator,
)
from .marc_rules import Rule


@marc_field_validator(get_control_field_length_errors)
def validate_length(data: str, info: ValidationInfo) -> None: ...  # pragma: no cover


@marc_field_validator(get_control_field_value_errors)
def validate_values(data: str, info: ValidationInfo) -> None: ...  # pragma: no cover


@marc_field_validator(get_indicator_errors)
def validate_indicators(
    data: Union[PydanticIndicators, Sequence], info: ValidationInfo
) -> None: ...  # pragma: no cover


@marc_field_validator(get_subfield_errors)
def validate_subfields(
    data: list[PydanticSubfield], info: ValidationInfo
) -> None: ...  # pragma: no cover


class ControlField(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a control field in a MARC record. The `tag` attribute is
    a three-digit string and the `data` attribute is a string that represents the
    value of the control field. The `rules` attribute contains the custom validation
    logic the particular MARC field and is computed passed to the `ControlField` model
    when it is called within a `MarcRecord` model. The `rules` attribute is not
    validated nor is it included in serialization.

    Attributes:
        rules:
            A `Rule` or dictionary that represents the MARC rules for the specified
            field
        tag:
            A three-digit string that represents the control field's tag.
        data:
            A string that represents the value of the control field. The `data`
            field's custom validator confirms that the `data` attribute is the expected
            length.
    """

    rules: Annotated[Union[Rule, dict[str, Any], None], Field(exclude=True)]

    tag: Literal["001", "002", "003", "004", "005", "006", "007", "008", "009"]
    data: Annotated[
        str, AfterValidator(validate_length), AfterValidator(validate_values)
    ]

    @model_serializer(when_used="unless-none")
    def serialize_control_field(self) -> dict[str, str]:
        """Serialize the control field into a dictionary with the correct format."""
        return {self.tag: self.data}


class DataField(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a data field in a MARC record. This can be used for all
    MARC fields when validating a record against MARC rules. The `tag` attribute
    is a three-digit string. The `indicators` attribute is a tuple of single digit
    strings represented by a `PydanticIndicators` or a `Sequence` object. The
    `subfields` attribute is a list of `PydanticSubfield` objects. The `rules`
    attribute contains the custom validation logic the particular MARC field and is
    computed passed to the `ControlField` model when it is called within a `MarcRecord`
    model. The `rules` attribute is not validated nor is it included in serialization.

    The `indicators` and `subfields` attributes have custom validators that confirm that
    the field`s attributes conform to the MARC rules for that given field.

    Attributes:
        rules:
            A `Rule` or dictionary that represents the MARC rules for the specified
            field
        tag:
            A three-digit string that represents the data field's tag.
        indicators:
            A `PydanticIndicators` object or a `Sequence` object representing the
            field's indicators.
        subfields:
            A list of `PydanticSubfield` objects.

    """

    rules: Annotated[Union[Rule, dict[str, Any], None], Field(exclude=True)]

    tag: Annotated[str, Field(pattern=r"0[1-9]\d|[1-9]\d\d")]
    indicators: Annotated[
        Union[PydanticIndicators, Sequence], AfterValidator(validate_indicators)
    ]
    subfields: Annotated[list[PydanticSubfield], AfterValidator(validate_subfields)]

    @model_serializer
    def serialize_data_field(
        self,
    ) -> dict[str, dict[str, Union[str, list[dict[str, str]]]]]:
        """Serialize the data field into a dictionary with the correct format."""
        return {
            self.tag: {
                "ind1": self.indicators[0],
                "ind2": self.indicators[1],
                "subfields": [i.model_dump() for i in self.subfields],
            }
        }
