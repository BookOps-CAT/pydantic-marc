"""Models to define rules used to validate MARC record objects.

Models defined in this module include:

`Rule`:
    a model to define valid attributes of an individual MARC field.
`RuleSet`:
    a model to define a set of rules to be used to validate a MARC record
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import Annotated, Any, Union

from pydantic import BaseModel, Field, computed_field, field_validator


def determine_material_type(leader: Union[str, None] = None) -> Union[str, None]:
    """
    Determine the material type from a MARC record's leader.

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


@lru_cache
def default_rules_from_json() -> dict[str, Any]:
    data = (
        resources.files("pydantic_marc")
        .joinpath("validation_rules/default_rules.json")
        .read_text(encoding="utf-8")
    )
    return json.loads(data)


def default_rules(data: dict[str, Any]) -> dict[str, Any]:
    rules: dict[str, Any] = {}
    leader = data.get("leader_data")
    context = data.get("context")
    if context and "rules" in context:
        for k, v in context["rules"].items():
            rules[k] = Rule(**{**v, "tag": v.get("tag", k)})
        if context.get("replace_all"):
            return rules
    material_type = determine_material_type(leader)
    data_dict = default_rules_from_json()
    for k, v in data_dict.items():
        if isinstance(v, dict) and material_type in v.keys():
            v = Rule(**v[material_type])
        elif (
            isinstance(v, dict)
            and material_type not in v.keys()
            and "tag" not in v.keys()
        ):
            v = {key: Rule(**val) for key, val in v.items()}
        else:
            v = Rule(**v)
        if k not in rules:
            rules[k] = v
    return rules


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


class RuleSet(BaseModel, frozen=True):
    context: Annotated[Union[Any, None], Field(exclude=True, default=None)]
    leader_data: Annotated[Union[str, None], Field(exclude=True, default=None)]
    rules: Annotated[
        dict[str, Union[Rule, dict[str, Rule]]],
        Field(default_factory=lambda data: default_rules(data)),
    ]

    @field_validator("rules", mode="before")
    @classmethod
    def get_rules(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Convert dictionary passed to `RuleSet.rules` attribute if needed"""
        rules: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(v, Rule):
                rules[k] = v
            elif k in ["006", "007", "008"] and isinstance(v, dict):
                for key, val in v.items():
                    if isinstance(val, Rule):
                        rules[k] = {key: val}
                    elif isinstance(val, dict):
                        rules[k] = {key: Rule(**val)}
                    else:
                        rules[k] = Rule(**v)
            else:
                rules[k] = Rule(**v)
        return rules

    @computed_field  # type: ignore[prop-decorator]
    @property
    def non_repeatable_fields(self) -> list[str]:
        """A list of tags for fields that are not repeatable in the RuleSet."""
        fields = []
        for tag, rule in self.rules.items():
            if isinstance(rule, Rule) and rule.repeatable is False:
                fields.append(tag)
            elif isinstance(rule, dict):
                fields.extend(
                    [
                        tag
                        for subtag, subrule in rule.items()
                        if isinstance(subrule, Rule) and subrule.repeatable is False
                    ]
                )
        return fields

    @computed_field  # type: ignore[prop-decorator]
    @property
    def required_fields(self) -> list[str]:
        """A list of tags for fields that are required in the RuleSet."""
        fields = []
        for tag, rule in self.rules.items():
            if isinstance(rule, Rule) and rule.required is True:
                fields.append(tag)
            elif isinstance(rule, dict):
                fields.extend(
                    [
                        tag
                        for subtag, subrule in rule.items()
                        if isinstance(subrule, Rule) and subrule.required is True
                    ]
                )
        return fields
