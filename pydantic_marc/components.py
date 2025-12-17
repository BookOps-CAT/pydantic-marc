"""Models that define components of MARC record objects.

Models defined in this module include:

`PydanticIndicators`:
    a model to validate the structure of the `indicators` attribute of a
    `DataField` object.
`PydanticSubfield`:
    a model to validate a the structure of the `subfields` attribute of a
    `DataField` object.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, model_serializer


class PydanticIndicators(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a set of indicators for a `DataField` object. Each indicator
    must be an empty string or a single character string.

    Attributes:
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
    must contain a `code` attribute as a single character string and a `value`
    attribute.

    Attributes:
        code: The subfield's code. Must be a single character string.
        value: The data contained within a subfield.

    """

    code: Annotated[str, Field(min_length=1, max_length=1)]
    value: str

    @model_serializer(when_used="unless-none")
    def serialize_subfield(self) -> dict[str, str]:
        """Serialize a subfield into a dict with the correct format."""
        return {self.code: self.value}
