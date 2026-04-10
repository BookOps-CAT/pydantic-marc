"""Classes to define rules used to validate MARC record objects.

Objects defined in this module include:

`RuleSet`:
    a class that defines a set of rules to be used to validate a MARC record
"""

from __future__ import annotations

import json
from functools import cached_property
from importlib import resources
from typing import Any, Union


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
        self.context = context or {}
        self.leader_data = leader_data
        self.rules = self._set_rules(rules or {})

    @cached_property
    def default_rules(self) -> dict[str, Any]:
        data = (
            resources.files("pydantic_marc")
            .joinpath("validation_rules/default_rules.json")
            .read_text(encoding="utf-8")
        )
        loaded = json.loads(data)

        defaults = {}
        mt = self.material_type
        for k, v in loaded.items():
            if mt in v:
                defaults[k] = v[mt]
            elif "tag" not in v:
                defaults[k] = {kk: vv for kk, vv in v.items()}
            else:
                defaults[k] = v
        return defaults

    def _normalize(self, data: dict[str, Any]) -> dict[str, Any]:
        return {k: {**v, "tag": v.get("tag", k)} for k, v in data.items()}

    def _set_rules(self, value: dict[str, Any]) -> dict[str, dict[str, Any]]:
        # If explicit rules are provided they are the only rules used.
        if value:
            return self._normalize(value)

        # If rules are passed as context they are used
        context_rules = self._normalize(self.context.get("rules", {}))

        # If context also has passed 'replace_all' then only they will be used
        if self.context.get("replace_all"):
            return context_rules

        # Otherwise default rules are added to the context rules without replacing any
        context_rules.update(
            {k: v for k, v in self.default_rules.items() if k not in context_rules}
        )

        return context_rules

    @property
    def non_repeatable_fields(self) -> list[str]:
        """A list of tags for fields that are not repeatable in the RuleSet."""
        return [
            tag
            for tag, rule in self.rules.items()
            if isinstance(rule, dict) and rule.get("repeatable", True) is False
        ]

    @property
    def required_fields(self) -> list[str]:
        """A list of tags for fields that are required in the RuleSet."""
        return [
            tag
            for tag, rule in self.rules.items()
            if isinstance(rule, dict) and rule.get("required", False) is True
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
