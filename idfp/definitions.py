from enum import Enum
from dataclasses import dataclass

import pydantic

from idfp.models import Area, Strain


class Type(str, Enum):
    AREA = "area"
    STRAIN = "strain"

# might be `_id`?
CSV_ID_FIELD = "id"


@dataclass
class TypeConfig:
    model: pydantic.BaseModel
    primary_key: str
    csv_table: str
    table: str


@dataclass
class Source:
    id: int
    type: Type


DATA_MAPPING = {
    Type.AREA: TypeConfig(**{
        "model": Area,
        "primary_key": "externalidentifier",
        "csv_table": "area_csv",
        "table": "areas",
    }),
    Type.STRAIN: TypeConfig(**{
        "model": Strain,
        "primary_key": "strainid",
        "csv_table": "strain_csv",
        "table": "strains",
    }),
}
