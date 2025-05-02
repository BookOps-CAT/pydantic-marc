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
from types import MappingProxyType
from typing import Annotated, Any, ClassVar, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class _DefaultRules:
    """Used to generate a default set of MARC rules from rules/default.json"""

    _cached_rules = None

    @classmethod
    def rules_from_json(cls) -> Dict[str, Any]:
        if cls._cached_rules is None:
            with open("pydantic_marc/validation_rules/default_rules.json", "r") as fh:
                cls._cached_rules = json.load(fh)
        return cls._cached_rules


class Rule(BaseModel, frozen=True):
    """
    A collection of rules used to validate the content of an individual MARC field.
    """

    _default: ClassVar[Mapping] = MappingProxyType(_DefaultRules.rules_from_json())

    tag: Annotated[str, Field(pattern=r"\d\d\d")]
    repeatable: Union[bool, None] = None
    ind1: Union[List[str], None] = None
    ind2: Union[List[str], None] = None
    subfields: Union[Dict[str, List[str]], None] = None
    length: Union[int, Dict[str, Union[int, List[int]]], None] = None
    required: Union[bool, None] = None

    @classmethod
    def create_default(cls, tag: str) -> Optional[Rule]:
        data = cls._default.get(tag, None)
        if data is not None:
            return Rule(**data)
        else:
            return data


class RuleSet(BaseModel, frozen=True):
    _default: ClassVar[Mapping] = MappingProxyType(_DefaultRules.rules_from_json())

    rules: Dict[str, Union[Rule, Any]] = {k: Rule(**v) for k, v in _default.items()}
    replace: bool = False

    @classmethod
    def from_validation_info(cls, info: ValidationInfo) -> Union[RuleSet, None]:
        """
        Create a `RuleSet` from a `ValidationInfo` object to be used in validating
        a `MarcRecord` model and the `ControlField` and `DataField` objects contained
        within it.

        The function identifies which rules to use in validation by checking two places
        for MARC rules: the model's validation context, and the model's `rules` attribute.

        This function first checks if MARC rules were passed to the model via validation
        context (indentified in the `ValidationInfo.context`attribute). It then checks the
        rules passed to the model via the `MarcRecord.rules` attribute. If a value was not
        passed to the `MarcRecord.rules` attribute then the default value `RuleSet` will be
        used.
        """
        rules = {}
        context = info.context

        if context and "rules" in context:
            for k, v in context["rules"].items():
                rules[k] = Rule(**{**v, "tag": v.get("tag", k)})
            if context.get("replace"):
                return RuleSet(rules=rules)
        record_rules = info.data["rules"]
        if not record_rules and not rules:
            return None
        rules.update({k: v for k, v in record_rules.rules.items() if k not in rules})
        return RuleSet(rules=rules)

    @field_validator("rules", mode="before")
    @classmethod
    def get_rules(cls, data: Dict[str, Union[Rule, Dict[str, Any]]]) -> Dict[str, Rule]:
        """Convert dictionary passed to `RuleSet.rules` attribute if needed"""
        rules = {}
        for k, v in data.items():
            if isinstance(v, Rule):
                rules[k] = v
            else:
                rules[k] = Rule(**v)
        return rules
