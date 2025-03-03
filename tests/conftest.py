import pytest

from pymarc import Indicators, Record, Subfield
from pymarc import Field as PymarcField


@pytest.fixture
def fake_marc_rules_str() -> str:
    return """009\tNR\tFAKE CONTROL FIELD 1\nlength\t12\t\nind1\tblank\tUndefinedind2\tblank\tUndefined\n\tNR\tUndefined\n\n900\tR\tFAKE FIELD 1\nind1\tb01\tIndicator 1\nind2\tblank\tUndefined\nsubfield\ta\tValid Subfields\na\tNR\tSubfield a\n\n901\tR\tFAKE FIELD 2\nind1\tblank\tUndefined\nind2\tblank\tUndefined\nsubfield\tab\tValid Subfields\na\tR\tSubfield a\nb\tNR\tSubfield b\n"""


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
