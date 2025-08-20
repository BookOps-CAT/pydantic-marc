"""A model that defines a valid MARC record.

The `MarcRecord` model can be used to validate that an object conforms
to the MARC21 format for bibliographic data.
"""

from __future__ import annotations

from typing import Annotated, Any, Dict, List, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    Discriminator,
    Field,
    Tag,
    WrapValidator,
    model_serializer,
)

from pydantic_marc.fields import ControlField, DataField
from pydantic_marc.marc_rules import RuleSet
from pydantic_marc.validators import validate_leader, validate_marc_fields


def field_discriminator(data: Any) -> str:
    """
    A function used to determine whether to validate a field against the `ControlField`
    model or the `DataField` model. All `00x` fields will be validated against the
    `ControlField` model and all other fields will be validated against the `DataField`
    model.

    Args:
        data: An object within the list passed to the `MarcRecord.fields` attribute.

    Returns:
        A string. Either 'control_field' or 'data_field'.
    """
    tag = getattr(data, "tag", data.get("tag"))
    if tag and tag.startswith("00"):
        return "control_field"
    else:
        return "data_field"


class MarcRecord(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a MARC record. The `leader` attribute will validate that the
    record's leader is a string and that it matches the pattern defined by the MARC
    standard. The `fields` attribute is a list of `ControlField` and `DataField`
    objects.

    Attributes:
        rules: The rules that define a valid MARC record as a `RuleSet` or dictionary.
        leader: A string representing a MARC record's leader.
        fields: A list of `ControlField` and `DataField` objects.
    """

    rules: Annotated[
        Union[RuleSet, Dict[str, Any], None],
        Field(default_factory=RuleSet, exclude=True),
    ]
    leader: Annotated[str, BeforeValidator(validate_leader)]
    fields: Annotated[
        List[
            Annotated[
                Union[
                    Annotated[ControlField, Tag("control_field")],
                    Annotated[DataField, Tag("data_field")],
                ],
                Discriminator(field_discriminator),
            ],
        ],
        WrapValidator(validate_marc_fields),
    ]

    @model_serializer
    def serialize_marc_record(self) -> Dict[str, Union[str, List[Any]]]:
        """Serialize a MARC record using the custom serializers for nested models"""
        return {
            "leader": str(self.leader),
            "fields": [field.model_dump() for field in self.fields],
        }
