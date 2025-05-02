"""Models that define components of MARC record objects.

Models defined in this module include:

`ControlField`:
    a model to validate MARC 00x fields. Contains `tag` and `data` attributes.
`DataField`:
    a model to validate all other MARC fields. Contains `tag`, `indicators`
    and `subfield` attributes.
`PydanticIndicators`:
    a model to validate the structure of the `indicators` attribute of a
    `DataField` object.
`PydanticSubfield`:
    a model to validate a the structure of the `subfields` attribute of a
    `DataField` object.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Literal, Sequence, Union

from pydantic import AfterValidator, BaseModel, Field, model_serializer

from pydantic_marc.rules import MARC_RULES
from pydantic_marc.validators import (
    validate_control_field,
    validate_indicators,
    validate_subfields,
)


class ControlField(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a control field in a MARC record. The `tag` attribute is
    a three-digit string and the `data` attribute is a string that represents the
    value of the control field. The `rules` attribute contains the custom validation
    logic the particular MARC field and is computed passed to the `ControlField` model
    when it is called within a `MarcRecord` model. The `rules` attribute is not validated nor is it included in serialization.

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

    rules: Annotated[
        Dict[str, Any],
        Field(
            default=MARC_RULES,
            exclude=True,
            json_schema_extra=lambda x: x.pop("default"),
        ),
    ]

    tag: Literal["001", "002", "003", "004", "005", "006", "007", "008", "009"]
    data: Annotated[str, AfterValidator(validate_control_field)]

    @model_serializer(when_used="unless-none")
    def serialize_control_field(self) -> Dict[str, str]:
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
            A `PydanticIndicators` object or a `Sequence` object representing the field's
            indicators.
        subfields:
            A list of `PydanticSubfield` objects.

    """

    rules: Annotated[
        Dict[str, Any],
        Field(
            default=MARC_RULES,
            exclude=True,
            json_schema_extra=lambda x: x.pop("default"),
        ),
    ]

    tag: Annotated[str, Field(pattern=r"0[1-9]\d|[1-9]\d\d")]
    indicators: Annotated[
        Union[PydanticIndicators, Sequence], AfterValidator(validate_indicators)
    ]
    subfields: Annotated[
        List[PydanticSubfield],
        AfterValidator(validate_subfields),
    ]

    @model_serializer
    def serialize_data_field(
        self,
    ) -> Dict[str, Dict[str, Union[str, List[Dict[str, str]]]]]:
        """Serialize the data field into a dictionary with the correct format."""
        return {
            self.tag: {
                "ind1": self.indicators[0],
                "ind2": self.indicators[1],
                "subfields": [{i.code: i.value} for i in self.subfields],
            }
        }


class PydanticIndicators(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a set of indicators for a `DataField` object. Each indicator
    must be an empty string or a single character string.

    Args:
        first: the field's first indicator as a 0-1 character string
        second: the field's second indicator as a 0-1 character string.

    """

    first: Annotated[str, Field(min_length=0, max_length=1)]
    second: Annotated[str, Field(min_length=0, max_length=1)]

    def __getitem__(self, index: int) -> str:
        return list(self.__dict__.values())[index]

    @model_serializer(when_used="unless-none")
    def serialize_indicators(self) -> tuple[str, str]:
        """Serialize indicators into a tuple with the correct format."""
        return (self.first, self.second)


class PydanticSubfield(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a single subfield within  a `DataField` object. Each subfield
    must contain a `code` attribute as a single character string and a `value` attribute.

    Args:
        code: The subfield's code. Must be a single character string.
        value: The data contained within a subfield.

    """

    code: Annotated[str, Field(min_length=1, max_length=1)]
    value: str

    @model_serializer(when_used="unless-none")
    def serialize_subfield(self) -> Dict[str, str]:
        """Serialize a subfield into a dict with the correct format."""
        return {self.code: self.value}
