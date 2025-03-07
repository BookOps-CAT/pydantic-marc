""""""

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
from pymarc import Leader as PymarcLeader

from pydantic_marc.fields import ControlField, DataField
from pydantic_marc.rules import MARC_RULES
from pydantic_marc.validators import validate_fields


def field_discriminator(v: Any) -> str:
    """
    A function used to determine whether to validate a field against the `ControlField`
    model or the `DataField` model. If `00x` fields will be validated against the
    `ControlField` model and all other fields will be validated against the `DataField`
    model.
    """
    tag = getattr(v, "tag", v.get("tag"))
    if tag and tag.startswith("00"):
        return "control_field"
    else:
        return "data_field"


class MarcRecord(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a MARC record. The `leader` attribute will validate that the
    record's leader is either a string or a pymarc.Leader object and that it matches
    the pattern defined by the MARC standard. The `fields` attribute is a list of
    `ControlField` and `DataField` objects.

    Attributes:
        rules: A dictionary representing the MARC rules that define a valid MARC record.
        leader: A string representing a MARC record's leader.
        fields: A list of `ControlField` and `DataField` objects.
    """

    rules: Annotated[
        Dict[str, Any],
        Field(
            default=MARC_RULES,
            exclude=True,
            json_schema_extra=lambda x: x.pop("default"),
        ),
    ]
    leader: Annotated[
        Union[PymarcLeader, str],
        Field(
            min_length=24,
            max_length=24,
            pattern=r"^[0-9]{5}[acdnp][acdefgijkmoprt][abcdims][\sa][\sa]22[0-9]{5}[\s12345678uzIKLM][\sacinu][\sabc]4500$",  # noqa E501
        ),
        BeforeValidator(lambda x: str(x)),
    ]
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
        WrapValidator(validate_fields),
    ]

    @model_serializer
    def serialize_marc_record(self) -> Dict[str, Union[str, List[Any]]]:
        """Serialize a MARC record using the serializers for nested models"""
        return {
            "leader": str(self.leader),
            "fields": [field.model_dump() for field in self.fields],
        }
