from pydantic import UUID4, BaseModel, ConfigDict, Field


class _ClosedModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PublicConstraint(_ClosedModel):
    key: str
    text: str


class PublicStakeholder(_ClosedModel):
    key: str
    name: str
    description: str


class PublicQuestionOption(_ClosedModel):
    key: str
    label: str
    description: str


class QuestionSummaryResponse(_ClosedModel):
    id: UUID4
    question_template_id: UUID4
    version_number: int = Field(gt=0)
    title: str
    question_type: str
    background_domain: str
    difficulty: str
    estimated_minutes: int = Field(ge=5, le=180)


class QuestionDetailResponse(QuestionSummaryResponse):
    scenario: str
    objective: str
    hard_constraints: tuple[PublicConstraint, ...]
    soft_constraints: tuple[PublicConstraint, ...]
    stakeholders: tuple[PublicStakeholder, ...]
    options: tuple[PublicQuestionOption, ...]
