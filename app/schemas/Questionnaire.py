from typing import Any, List, Dict, Optional
from typing import List, Union, Any, Annotated,Dict,Literal
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


class Coordinates(BaseModel):
    latitude: float
    longitude: float

      
class TripType(Enum):
    PLACE = "place"
    ROAD = "road"
    ZONE = "zone"


class LatLong(BaseModel):
    latitude: float
    longitude: float


class Road(BaseModel):
    origin: LatLong
    destination: LatLong


class Place(BaseModel):
    coordinates: LatLong
    place_name: str


class Zone(BaseModel):
    center: LatLong
    radius: int


class MustVisitPlace(BaseModel):
    place_id: str
    place_name: str
    coordinates: LatLong


class TripCreate(BaseModel):
    trip_id: str
    name: str
    data: Zone | Place | Road
    tripType: TripType
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
    tripType:TripType
    questionnaire: List[Answer]
    start_date: datetime
    end_date: datetime
    budget: float
    keywords: List[str] = []
    must_visit_places: Optional[List[MustVisitPlace]] = []

class TripResponse(BaseModel):
    itinerary: TripItinerary | RoadItinerary
    trip_type:str
    template_type: TemplateType
    generic_type_scores: Dict[str, float]
