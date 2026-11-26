"""Pydantic models: the contract between the LLM, the API and the frontend."""

from typing import Literal

from pydantic import BaseModel, Field

CEFR = Literal["A1", "A2", "B1", "B2", "C1", "C2"]
CEFR_ORDER: list[str] = ["A1", "A2", "B1", "B2", "C1", "C2"]

ErrorCategory = Literal[
    "verb_conjugation",
    "gender_agreement",
    "number_agreement",
    "ser_vs_estar",
    "por_vs_para",
    "preterite_vs_imperfect",
    "subjunctive",
    "prepositions",
    "articles",
    "word_order",
    "vocabulary",
    "spelling_accents",
    "other",
]


class Correction(BaseModel):
    original: str = Field(description="The exact incorrect fragment the learner wrote.")
    corrected: str = Field(description="The corrected Spanish fragment.")
    category: ErrorCategory
    explanation: str = Field(description="One or two sentences in English explaining the rule.")


class LevelEstimate(BaseModel):
    cefr: CEFR
    confidence: float = Field(ge=0.0, le=1.0, description="0 to 1. Low for very short messages.")
    reasoning: str = Field(description="Short English justification: vocabulary range, tenses used, accuracy.")


class Analysis(BaseModel):
    """Structured feedback on ONE learner message. Produced by the analysis call."""

    is_spanish: bool = Field(description="False if the learner wrote mostly in English.")
    corrections: list[Correction]
    corrected_message: str = Field(description="The learner's full message rewritten in natural, correct Spanish.")
    level: LevelEstimate
    encouragement: str = Field(description="One short, specific compliment in English.")


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    reply: str
    analysis: Analysis
    session_level: CEFR | None
