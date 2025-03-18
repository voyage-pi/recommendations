from typing import Any, List
from enum import Enum
from pydantic import BaseModel
from app.schemas.Activities import TripItinerary, TemplateType


class QuestionType(str, Enum):
    SCALE = "scale"
    SELECT = "select"


class Answer(BaseModel):
    question_id: int
    value: Any
    type: QuestionType


class Coordinates(BaseModel):
    latitude: float
    longitude: float


class TripCreate(BaseModel):
    coordinates: Coordinates
    questionnaire: List[Answer]


class TripResponse(BaseModel):
    id: int
    itinerary: TripItinerary
    template_type: TemplateType
