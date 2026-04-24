from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class ResearchDomain(str, Enum):
    COMPUTER_SCIENCE = "Computer Science"
    MEDICAL = "Medical"
    BUSINESS = "Business"
    SOCIAL_SCIENCES = "Social Sciences"
    ENGINEERING = "Engineering"
    NATURAL_SCIENCES = "Natural Sciences"
    OTHER = "Other"

class StudyType(str, Enum):
    EXPERIMENTAL = "Experimental"
    SYSTEM_DEVELOPMENT = "System Development"
    SURVEY = "Survey"
    CASE_STUDY = "Case Study"
    COMPARATIVE = "Comparative"
    OTHER = "Other"

class PaperInput(BaseModel):
    title: str
    abstract: str
    methodology: str
    results: Optional[str] = None
    conclusion: Optional[str] = None

class ComponentScore(BaseModel):
    score: int
    feedback: str
    issues: List[str] = []
    strengths: List[str] = []

class ReproducibilityAssessment(BaseModel):
    overall_score: int
    clarity: ComponentScore
    completeness: ComponentScore
    resource_availability: ComponentScore
    replicability: ComponentScore

class MethodologicalRigor(BaseModel):
    overall_score: int
    study_design: ComponentScore
    sample_adequacy: ComponentScore
    evaluation_validity: ComponentScore
    statistical_rigor: ComponentScore

class AssessmentResult(BaseModel):
    metadata: Dict[str, Any]
    reproducibility_assessment: ReproducibilityAssessment
    methodological_rigor: MethodologicalRigor
    identified_strengths: List[str]
    identified_weaknesses: List[str]
    recommendations: List[str]
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)

    def dict(self, *args, **kwargs):
        """Helper to ensure compatibility with older dict calls"""
        return super().model_dump(*args, **kwargs)