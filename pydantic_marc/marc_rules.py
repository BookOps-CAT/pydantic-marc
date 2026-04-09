"""Classes to define rules used to validate MARC record objects.

Objects defined in this module include:

`Rule`:
    a class that defines valid attributes of an individual MARC field.
`RuleSet`:
    a class that defines a set of rules to be used to validate a MARC record
"""

from __future__ import annotations

import json
from functools import cached_property
from importlib import resources
from typing import Any, Union


class Rule:
    """
    A collection of rules used to validate the content of an individual MARC field.
    """

    def __init__(
        self,
        tag: str,
        repeatable: Union[bool, None] = None,
        ind1: Union[list[str], None] = None,
        ind2: Union[list[str], None] = None,
        subfields: Union[dict[str, list[str]], None] = None,
        length: Union[int, dict[str, Union[int, list[int]]], None] = None,
        required: Union[bool, None] = None,
        field_values: Union[dict[str, Any], None] = None,
    ) -> None:
        self.tag = tag
        self.repeatable = repeatable
        self.ind1 = ind1
        self.ind2 = ind2
        self.subfields = subfields
        self.length = length
        self.required = required
        self.field_values = field_values


class RuleSet:
    MATERIAL_TYPE_MAPPING = {
        "c": "MU",
        "d": "MU",
        "i": "MU",
        "j": "MU",
        "e": "MP",
        "f": "MP",
        "g": "VM",
        "k": "VM",
        "o": "VM",
        "r": "VM",
        "m": "CF",
        "p": "MM",
    }
    CONTINUING_RESOURCES = {("a", "b"): "CR", ("a", "i"): "CR", ("a", "s"): "CR"}

    def __init__(
        self,
        context: Union[Any, None] = None,
        leader_data: Union[str, Any, None] = None,
        rules: dict[str, Any] = {},
    ) -> None:
        self.context = context
        self.leader_data = leader_data
        self.rules = self._set_rules(rules)

    @cached_property
    def default_rules(self) -> dict[str, Any]:
        data = (
            resources.files("pydantic_marc")
            .joinpath("validation_rules/default_rules.json")
            .read_text(encoding="utf-8")
        )
        return json.loads(data)

    def _set_rules(self, value: dict[str, Any]) -> dict[str, Rule]:
        rules = {}
        if value:
            for k, v in value.items():
                if isinstance(v, dict):
                    rules[k] = Rule(**v)
                else:
                    rules[k] = v
            return rules
        if self.context and "rules" in self.context:
            for k, v in self.context["rules"].items():
                rules[k] = Rule(**{**v, "tag": v.get("tag", k)})
            if self.context.get("replace_all"):
                return rules
        for k, v in self.default_rules.items():
            if isinstance(v, dict) and self.material_type in v.keys():
                v = Rule(**v[self.material_type])
            elif (
                isinstance(v, dict)
                and self.material_type not in v.keys()
                and "tag" not in v.keys()
            ):
                v = {key: Rule(**val) for key, val in v.items()}
            else:
                v = Rule(**v)
            if k not in rules:
                rules[k] = v
        return rules

    @property
    def non_repeatable_fields(self) -> list[str]:
        """A list of tags for fields that are not repeatable in the RuleSet."""
        return [
            tag
            for tag, rule in self.rules.items()
            if isinstance(rule, Rule) and rule.repeatable is False
        ]

    @property
    def required_fields(self) -> list[str]:
        """A list of tags for fields that are required in the RuleSet."""
        return [
            tag
            for tag, rule in self.rules.items()
            if isinstance(rule, Rule) and rule.required is True
        ]

    @property
    def material_type(self) -> Union[str, None]:
        """
        Determine the material type from a MARC record's leader.

        This function extracts the material type from the leader string based on the
        character at position 6. It maps specific characters to predefined material
        types used in MARC records.

        Args:
            leader:
                A string representing the MARC record leader.
        Returns:
            A string representing the material type, or `None` if the leader is invalid.
        """
        if not self.leader_data or len(self.leader_data) < 8:
            return None

        record_type = self.leader_data[6]
        subtype = self.leader_data[7]

        if record_type in self.MATERIAL_TYPE_MAPPING:
            return self.MATERIAL_TYPE_MAPPING[record_type]

        return self.CONTINUING_RESOURCES.get((record_type, subtype), "BK")
