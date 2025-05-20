from typing import Any, List, Dict, Optional
from typing import List, Union, Any,Dict,Literal
from enum import Enum
from pydantic import BaseModel,Field
from app.schemas.Activities import PlaceInfo, TripItinerary, TemplateType,RoadItinerary
from datetime import datetime

class QuestionType(str, Enum):
    SCALE = "scale"
    SELECT = "select"

class Answer(BaseModel):
    question_id: int
    value: Any
    type: QuestionType

class TripType(Enum):
    PLACE = "place"
    ROAD = "road"
    ZONE = "zone"


class LatLong(BaseModel):
    latitude: float
    longitude: float

class Road (BaseModel):
    type : Literal["road"]="road"
    origin:PlaceInfo 
    destination:PlaceInfo 
    polylines: str

class Zone(BaseModel):
    type : Literal["zone"]="zone"
    center: LatLong
    radius: int

class Place(BaseModel):
    type : Literal["place"]="place"
    coordinates: LatLong
    place_name: str

class TripCreate(BaseModel):
    trip_id: str
    name:str
    data: Union[Zone, Place, Road]= Field(descriminator="type")
    questionnaire: List[Answer]
    start_date: datetime
    end_date: datetime
    tripType:TripType
    budget: float
    keywords: List[str] = []
    must_visit_places: Optional[List[PlaceInfo]] = []
    is_group: bool

class TripResponse(BaseModel):
    itinerary: TripItinerary | RoadItinerary
    trip_type:str
    template_type: TemplateType
    generic_type_scores: Dict[str, float]
    id: str
    is_group: bool
