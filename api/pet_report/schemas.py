from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class PetInfo(BaseModel):
    name: Optional[str] = None
    breed: Optional[str] = None
    owner: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[str] = None
    sample_id: Optional[str] = None
    sample_type: Optional[str] = None
    test_package: Optional[str] = None
    receipt_date: Optional[str] = None
    report_date: Optional[str] = None
    test_type: Optional[str] = None


class KeyFinding(BaseModel):
    condition: Optional[str] = None
    gene: Optional[str] = None
    risk_level: Optional[str] = None
    inheritance: Optional[str] = None
    description: Optional[str] = None


class ImportantThing(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None


class AILetter(BaseModel):
    important_things: List[ImportantThing] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    days_30: List[str] = Field(default_factory=list, validation_alias="30days")
    days_90: List[str] = Field(default_factory=list, validation_alias="90days")
    tips: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class AIOverviewItem(BaseModel):
    title: Optional[str] = None
    icon: Optional[str] = None
    label: Optional[str] = None
    evidence: Optional[str] = None
    analysis: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class PetReportPayload(BaseModel):
    pet_type: Optional[str] = None
    pet_info: PetInfo = Field(default_factory=PetInfo)
    key_findings: List[KeyFinding] = Field(default_factory=list)
    AI_letter: Optional[AILetter] = None
    AI_overview: List[AIOverviewItem] = Field(default_factory=list)
    details: Dict[str, str] = Field(default_factory=dict)
    certification_number: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


def coerce_payload(data: Dict[str, Any]) -> PetReportPayload:
    return PetReportPayload.model_validate(data)
