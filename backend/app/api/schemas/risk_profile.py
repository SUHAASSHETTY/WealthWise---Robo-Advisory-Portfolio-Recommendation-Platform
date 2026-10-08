"""Risk profile request/response models (risk_profile_spec §4). Field names match the spec tables exactly.

The questionnaire models have no points, bands or caps fields: they cannot leak scoring rules to customers.
"""

from datetime import datetime

from pydantic import BaseModel

from app.domain.bands import RiskBand


class OptionOut(BaseModel):
    code: str
    label: str


class QuestionOut(BaseModel):
    code: str
    prompt: str
    order: int
    options: list[OptionOut]


class QuestionnaireOut(BaseModel):
    policy_version_id: str
    version_no: int
    questions: list[QuestionOut]


class AnswerIn(BaseModel):
    question_code: str
    option_code: str


class AssessmentIn(BaseModel):
    policy_version_id: str
    answers: list[AnswerIn]


class AssessmentOut(BaseModel):
    assessment_id: str
    total_score: int
    computed_band: RiskBand
    assigned_band: RiskBand
    applied_caps: list[str]
    policy_version_no: int
    created_at: datetime


class RiskProfileOut(BaseModel):
    risk_band: RiskBand
    source: str  # "ASSESSMENT" | "ADVISOR_OVERRIDE"
    source_id: str
    as_of: datetime


class NoRiskProfileOut(BaseModel):
    risk_band: None = None


class HistoryEntryOut(BaseModel):
    type: str  # "ASSESSMENT" | "ADVISOR_OVERRIDE"
    id: str
    band: RiskBand
    created_at: datetime
    policy_version_no: int | None = None
    reason_code: str | None = None
