"""Models to define rules used to validate MARC record objects.

Models defined in this module include:

`Rule`:
    a model to define valid attributes of an individual MARC field.
`RuleSet`:
    a model to define a set of rules to be used to validate a MARC record
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from importlib import resources
from types import MappingProxyType
from typing import Annotated, Any, ClassVar, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator


def determine_material_type(leader: str) -> Union[str, None]:
    """
    Determine the material type from a MARC record leader.

    This function extracts the material type from the leader string based on the
    character at position 6. It maps specific characters to predefined material types
    used in MARC records.

    Args:
        leader:
            A string representing the MARC record leader.
    Returns:
        A string representing the material type, or `None` if the leader is invalid.
    """
    if not leader or len(leader) < 8:
        return None
    record_type = leader[6:7]
    if record_type == "a" and leader[7:8] in ["b", "i", "s"]:
        return "CR"
    elif record_type in ["c", "d", "i", "j"]:
        return "MU"
    elif record_type in ["e", "f"]:
        return "MP"
    elif record_type in ["g", "k", "o", "r"]:
        return "VM"
    elif record_type == "m":
        return "CF"
    elif record_type == "p":
        return "MM"
    else:
        return "BK"


class _DefaultRules:
    """Used to generate a default set of MARC rules from rules/default.json"""

    _cached_rules = None

    @classmethod
    def rules_from_json(cls) -> dict[str, Any]:
        data = (
            resources.files("pydantic_marc")
            .joinpath("validation_rules/default_rules.json")
            .read_text(encoding="utf-8")
        )
        return json.loads(data)


class Rule(BaseModel, frozen=True, extra="allow"):
    """
    A collection of rules used to validate the content of an individual MARC field.
    """

    tag: Annotated[str, Field(pattern=r"\d\d\d|LDR")]
    repeatable: Union[bool, None] = None
    ind1: Union[list[str], None] = None
    ind2: Union[list[str], None] = None
    subfields: Union[dict[str, list[str]], None] = None
    length: Union[int, dict[str, Union[int, list[int]]], None] = None
    required: Union[bool, None] = None
    values: Union[dict[str, Any], None] = None
    material_type: Union[str, None] = None


class RuleSet(BaseModel, frozen=True):
    _default: ClassVar[Mapping] = MappingProxyType(_DefaultRules.rules_from_json())

    rules: dict[str, Union[Rule, Any]] = {k: Rule(**v) for k, v in _default.items()}

    @classmethod
    def from_validation_info(cls, info: ValidationInfo) -> Union[RuleSet, None]:
        """
        Create a `RuleSet` from a `ValidationInfo` object to be used in validating
        a `MarcRecord` model and the `ControlField` and `DataField` objects contained
        within it.

        The function identifies which rules to use in validation by checking two places
        for MARC rules: the model's validation context, and the model's `rules`
        attribute.

        This function first checks if MARC rules were passed to the model via validation
        context (indentified in the `ValidationInfo.context`attribute). It then checks
        the rules passed to the model via the `MarcRecord.rules` attribute. If a value
        was not passed to the `MarcRecord.rules` attribute then the default value
        `RuleSet` will be used.
        """
        rules = {}
        context = info.context

        if context and "rules" in context:
            for k, v in context["rules"].items():
                rules[k] = Rule(**{**v, "tag": v.get("tag", k)})
            if context.get("replace_all"):
                return RuleSet(rules=rules)
        record_rules = info.data["rules"]
        if not record_rules and not rules:
            return None
        material_type = determine_material_type(info.data.get("leader", ""))
        for k, v in record_rules.rules.items():
            if material_type and k in ["006", "008"] and v.model_extra:
                rule_dict = v.model_dump()
                type_vals = rule_dict.get("material_types", {}).get(material_type, {})
                rule_dict.update(type_vals)
                v = Rule(**rule_dict)
            if k not in rules:
                rules[k] = v
        return RuleSet(rules=rules)

    @field_validator("rules", mode="before")
    @classmethod
    def get_rules(cls, data: dict[str, Union[Rule, dict[str, Any]]]) -> dict[str, Rule]:
        """Convert dictionary passed to `RuleSet.rules` attribute if needed"""
        rules = {}
        for k, v in data.items():
            rules[k] = v if isinstance(v, Rule) else Rule(**v)
        return rules
