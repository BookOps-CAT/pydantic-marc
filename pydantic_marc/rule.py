"""Classes to define rules used to validate a MARC field.

Objects defined in this module include:

`Rule`:
    a class that defines valid attributes of an individual MARC field.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass
class Rule:
    """
    A collection of rules used to validate the content of an individual MARC field.
    """

    tag: str
    repeatable: Union[bool, None] = None
    ind1: Union[list[str], None] = None
    ind2: Union[list[str], None] = None
    subfields: Union[dict[str, list[str]], None] = None
    length: Union[int, dict[str, Union[int, list[int]]], None] = None
    required: Union[bool, None] = None
    field_values: Union[dict[str, Any], None] = None
