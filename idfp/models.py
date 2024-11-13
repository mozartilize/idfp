import typing as t
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class Area(BaseModel):
    CreatedBy: str = Field(max_length=35)
    UpdatedBy: t.Optional[str] = Field(max_length=35)
    CreatedDate: date
    UpdatedDate: t.Optional[date]
    LicenseeId: int
    ExternalIdentifier: str = Field(max_length=100)
    Name: str = Field(max_length=75)
    AreaId: int
    IsQuarantine: bool


class StrainType(str, Enum):
    Indica = "Indica"
    Sativa = "Sativa"
    Hybrid = "Hybrid"


class Strain(BaseModel):
    CreatedBy: str = Field(max_length=35)
    UpdatedBy: t.Optional[str] = Field(max_length=35)
    CreatedDate: date
    UpdatedDate: t.Optional[date]
    LicenseeId: int
    StrainId: int
    AssociateId: int
    StrainType: StrainType
    Name: str = Field(max_length=50)
