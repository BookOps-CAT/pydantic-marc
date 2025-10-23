from typing import Any, Optional

import pytest
from pymarc import Field as PymarcField
from pymarc import Indicators, Record, Subfield

from pydantic_marc.marc_rules import Rule, RuleSet


@pytest.fixture
def get_default_rule():
    rules = RuleSet()

    def _get_default_rule(tag: str, subtype: Optional[str] = None):
        if subtype is None:
            return rules.rules.get(tag)
        rule = rules.rules.get(tag, {})
        return Rule(
            tag=tag,
            length=rule.material_types.get(subtype, {}).get("length"),
            values=rule.material_types.get(subtype, {}).get("values"),
            repeatable=rule.repeatable,
            required=rule.required,
        )

    return _get_default_rule


@pytest.fixture
def make_mock_info():
    class MockInfo:
        def __init__(
            self,
            data: dict[str, Any],
            field_name: str,
            context: Optional[dict[str, Any]] = None,
        ):
            self.data = data
            self.field_name = field_name
            self.context = context

    def _make_mock_info(
        data: dict[str, Any], field_name: str, context: Optional[dict[str, Any]] = None
    ):
        if "leader" not in data:
            data["leader"] = "00454cam a22001575i 4500"
        return MockInfo(data=data, context=context, field_name=field_name)

    return _make_mock_info


@pytest.fixture
def stub_record() -> Record:
    bib = Record()
    bib.leader = "00454cam a22001575i 4500"
    bib.add_field(PymarcField(tag="001", data="on1381158740"))
    bib.add_field(
        PymarcField(tag="008", data="190306s2017    ht a   j      000 1 hat d")
    )
    bib.add_field(
        PymarcField(
            tag="050",
            indicators=Indicators(" ", "4"),
            subfields=[
                Subfield(code="a", value="F00"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="245",
            indicators=Indicators("0", "0"),
            subfields=[
                Subfield(code="a", value="Title :"),
                Subfield(
                    code="b",
                    value="subtitle /",
                ),
                Subfield(
                    code="c",
                    value="Author",
                ),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="300",
            indicators=Indicators(" ", " "),
            subfields=[
                Subfield(code="a", value="100 pages :"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="910",
            indicators=Indicators(" ", " "),
            subfields=[
                Subfield(code="a", value="RL"),
            ],
        )
    )
    return bib


@pytest.fixture
def stub_invalid_record() -> Record:
    """
    Record has the following errors:
        - LDR is missing 7 characters
        - Multiple 1xx fields are present (100 and 110)
        - There is no 245 field
        - The 006 field is too short
        - 336 field has invalid ind1 and ind2
        - 336 contains an invalid subfield ($z)
        - 600 has more than one $a
    """
    bib = Record()
    bib.leader = "01632cam a2200529       "
    bib.add_field(PymarcField(tag="001", data="1234567890"))
    bib.add_field(PymarcField(tag="001", data="1234567890"))
    bib.add_field(PymarcField(tag="006", data="p|||||"))
    bib.add_field(
        PymarcField(tag="008", data="240911s2023    lv a     bc   000 0dlat d")
    )
    bib.add_field(
        PymarcField(
            tag="100",
            indicators=Indicators("1", ""),
            subfields=[
                Subfield(code="a", value="Foo"),
                Subfield(code="e", value="author"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="110",
            indicators=Indicators("1", ""),
            subfields=[
                Subfield(code="a", value="Bar"),
                Subfield(code="e", value="publisher"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="300",
            indicators=Indicators(" ", " "),
            subfields=[
                Subfield(code="a", value="100 pages :"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="336",
            indicators=Indicators("1", "1"),
            subfields=[
                Subfield(code="a", value="still image"),
                Subfield(code="b", value="sti"),
                Subfield(code="2", value="rdacontent"),
                Subfield(code="z", value="foo"),
            ],
        )
    )
    bib.add_field(
        PymarcField(
            tag="600",
            indicators=Indicators("1", "0"),
            subfields=[
                Subfield(code="a", value="Foo, Bar,"),
                Subfield(code="a", value="Foo, Bar,"),
                Subfield(code="d", value="2000-2020"),
            ],
        )
    )
    return bib


@pytest.fixture
def stub_record_invalid_300(stub_record) -> PymarcField:
    stub_record.remove_fields("300")
    stub_record.add_field(
        PymarcField(
            tag="300",
            indicators=Indicators("1", "0"),
            subfields=[Subfield(code="h", value="foo")],
        )
    )
    return stub_record
