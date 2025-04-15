from typing import Any, List, Dict,Optional
from enum import Enum
from pydantic import BaseModel
from app.schemas.Activities import TripItinerary, TemplateType
from app.schemas.GenericTypes import GenericType
from datetime import datetime


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

class TripType(Enum):
    PLACE= "place"
    ROAD = "road"
    ZONE = "zone"

class LatLong(BaseModel):
    latitude:float
    longitude:float

class Road(BaseModel):
    origin:LatLong
    destination:LatLong

class Place(BaseModel):
    coordinates:LatLong

class Zone(BaseModel):
    center:LatLong
    radius:int

class TripCreate(BaseModel):
    data: Zone | Place | Road
    tripType:TripType
    questionnaire: List[Answer]
    start_date: datetime
    end_date: datetime
    budget: float

class TripResponse(BaseModel):
    id: int
    itinerary: TripItinerary
    template_type: TemplateType
    generic_type_scores: Dict[str, float]
