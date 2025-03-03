""""""

from __future__ import annotations
from typing import Annotated, Any, Dict, List, Literal, Union
from pydantic import (
    AfterValidator,
    BeforeValidator,
    BaseModel,
    Discriminator,
    Field,
    model_serializer,
    Tag,
    WrapValidator,
)
from pymarc import Indicators as PymarcIndicators
from pymarc import Leader as PymarcLeader
from pymarc import Subfield as PymarcSubfield
from pydantic_marc.rules import MARC_RULES
from pydantic_marc.validators import (
    validate_control_field,
    validate_fields,
    validate_indicators,
    validate_subfields,
)


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


def remove_default(field_properties: Dict[str, Any]):
    field_properties.pop("default")


class ControlField(BaseModel, arbitrary_types_allowed=True, from_attributes=True):
    """
    A class that defines a control field in a MARC record. The `tag` attribute is
    a three-digit string and the `data` attribute is a string that represents the
    value of the control field. The `rules` attribute is a dictionary that contains
    rules for the particular MARC field and is computed by looking up the tag within
    the `MARC_RULES` dictionary. The `rules` attribute is not validated nor is it
    included in serialization.

    Attributes:
        tag: A three-digit string that represents the control field tag.
        data: A string that represents the value of the control field.
        rules: A dictionary that represents the MARC standard for a particular field
    """

    rules: Annotated[
        Dict[str, Any],
        Field(default=MARC_RULES, exclude=True, json_schema_extra=remove_default),
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
    strings represented by a pymarc.Indicators object. The `subfields` attribute
    is a list of pymarc.Subfield objects. The `rules` attribute is a dictionary that
    contains rules for the particular MARC field and is computed by looking up the
    tag within the `MARC_RULES` dictionary. The `rules` attribute is not validated
    nor is it included in serialization.

    Attributes:
        tag: A three-digit string that represents the field's tag.
        indicators: A tuple of one-character strings representing field's indicators.
        subfields: a list of dictionaries or pymarc.Subfield objects.
        rules: A dictionary that represents the MARC standard for a particular field
    """

    rules: Annotated[
        Dict[str, Any],
        Field(default=MARC_RULES, exclude=True, json_schema_extra=remove_default),
    ]

    tag: Annotated[str, Field(pattern=r"0[1-9]\d|[1-9]\d\d")]
    indicators: Annotated[PymarcIndicators, AfterValidator(validate_indicators)]
    subfields: Annotated[List[PymarcSubfield], AfterValidator(validate_subfields)]

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
        Field(default=MARC_RULES, exclude=True, json_schema_extra=remove_default),
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
