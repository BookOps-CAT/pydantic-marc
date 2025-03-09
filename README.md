# pydantic-marc
pydantic-marc is a library for validating data against the MARC21 Format for Bibliographic Data.  

## Installation

Use pip:

`$ pip install pydantic-marc`

## Features

pydantic-marc uses `pydantic`, the popular data validation library, to define the valid components of a MARC record. The package expects users will employ `pymarc` to read MARC records from binary files.

### Basic usage:

Validating a MARC record:
```python
from pymarc import MARCReader

from pydantic_marc import MarcRecord


with open("temp/valid.mrc", "rb") as fh:
    reader = MARCReader(fh)
    for record in reader:
        print(record)
        model = MarcRecord.model_validate(record, from_attributes=True)
        print(model.model_dump())
```
```json
{
    "leader": "00536nam a22001985i 4500",
    "fields": [
        {"001": "123456789"},
        {"008": "201201s2020    nyua          000 1 eng d"},
        {"035": {"ind1": " ", "ind2": " ", "subfields": [{"a": "(OCoLC)1234567890"}]}},
        {"049": {"ind1": " ", "ind2": " ", "subfields": [{"a": "NYPP"}]}},
        {
            "245": {
                "ind1": "0",
                "ind2": "0",
                "subfields": [
                    {"a": "Fake :"},
                    {"b": "Marc Record"},
                ]
            }
        },
        {
            "264": {
                "ind1": " ",
                "ind2": "1",
                "subfields": [
                    {"a": "New York :"},
                    {"b": "NY,"},
                    {"c": "[2020]"}
                ]
            }
        },
        {
            "300": {
                "ind1": " ",
                "ind2": " ",
                "subfields": [{"a": "100 pages :"}, {"b": "color illustrations;"}, {"c": "30 cm"}]
            }
        },
        {"336": {"ind1": " ", "ind2": " ", "subfields": [{"a": "text"}, {"b": "txt"}, {"2": "rdacontent"}]}},
        {"337": {"ind1": " ", "ind2": " ", "subfields": [{"a": "unmediated"}, {"b": "n"}, {"2": "rdamedia"}]}},
        {"338": {"ind1": " ", "ind2": " ", "subfields": [{"a": "volume"}, {"b": "nc"}, {"2": "rdacarrier"}]}}
        
    ]
}
```
If the record is invalid the errors can be returned as json, a dictionary, or in a human-readable format.

JSON Error Message:
```python
from pydantic import ValidationError
from pymarc import MARCReader

from pydantic_marc import MarcRecord

with open("temp/invalid.mrc", "rb") as fh:
    reader = MARCReader(fh)
    for record in reader:
        print(record)
        try:
            MarcRecord.model_validate(record, from_attributes=True)
        except ValidationError as e:
            # errors as a dictionary
            print(e.errors())

            # errors as json
            print(e.json())
```
```json
[
    {
        "type": "non_repeatable_field",
        "loc": ("fields", "001"),
        "msg": "001: Has been marked as a non-repeating field.",
        "input": "001",
        "ctx": {"input": "001"}
    },
    {
        "type": "missing_required_field",
        "loc": ("fields", "245"),
        "msg": "One 245 field must be present in a MARC21 record.",
        "input": "245",
        "ctx": {"input": "245"}
    },
    {
        "type": "multiple_1xx_fields",
        "loc": ("fields", "100", "110"),
        "msg": "1XX: Only one 1XX tag is allowed. Record contains: ['100', '110']",
        "input": ["100", "110"],
        "ctx": {"input": ["100", "110"]}
    },
    {
        "type": "control_field_length_invalid",
        "loc": ("fields", "006"),
        "msg": "006: Length appears to be invalid. Reported length is: 6. Expected length is: 18",
        "input": "p    |",
        "ctx": {"tag": "006", "valid": 18, "input": "p    |", "length": 6}
    },
    {
        "type": "invalid_indicator",
        "loc": ("fields", "035", "ind1"),
        "msg": "035 ind1: Invalid data (0). Indicator should be ['', ' '].",
        "input": "0",
        "ctx": {"loc": ("035", "ind1"), "input": "0", "valid": ["", " "], "tag": "035", "ind": "ind1"}
    },
    {
        "type": "non_repeatable_subfield",
        "loc": ("fields", "600", "a"),
        "msg": "600 $a: Subfield cannot repeat.",
        "input": [PydanticSubfield(code="a", value="Foo"), PydanticSubfield(code="a", value="Foo,")],
        "ctx": {
            "loc": ("600", "a"),
            "input": [PydanticSubfield(code="a", value="Foo"), PydanticSubfield(code="a", value="Foo,")],
            "tag": "600",
            "code": "a"
        }
    }
]
```
Human-readable Error Message:
```python
from pydantic import ValidationError
from pymarc import MARCReader

from pydantic_marc import MarcRecord

with open("temp/invalid.mrc", "rb") as fh:
    reader = MARCReader(fh)
    for record in reader:
        print(record)
        try:
            MarcRecord.model_validate(record, from_attributes=True)
        except ValidationError as e:
            # errors in a human-readable format
            print(e.errors())

```
```text
6 validation errors for MarcRecord
fields.001
  001: Has been marked as a non-repeating field. [type=non_repeatable_field, input_value='001', input_type=str]
fields.245
  One 245 field must be present in a MARC21 record. [type=missing_required_field, input_value='245', input_type=str]
fields.100.110
  1XX: Only one 1XX tag is allowed. Record contains: ['100', '110'] [type=multiple_1xx_fields, input_value=['100', '110'], input_type=list]
fields.006
  006: Length appears to be invalid. Reported length is: 6. Expected length is: 18 [type=control_field_length_invalid, input_value='p    |', input_type=str]
fields.035.ind1
  035 ind1: Invalid data (0). Indicator should be ['', ' ']. [type=invalid_indicator, input_value='0', input_type=str]
fields.600.a
  600 $a: Subfield cannot repeat. [type=non_repeatable_subfield, input_value=[PydanticSubfield(code='a...code='a', value='Foo,')], input_type=list]
```
