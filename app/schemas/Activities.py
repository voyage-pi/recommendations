from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel, root_validator
import json
import os


def load_activity_types():
    config_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(config_dir, "activity_types.json"), "r") as f:
        return json.load(f)


_activity_data = load_activity_types()
_activity_types = list(_activity_data.get("durations", {}).keys())

ActivityType = Enum(
    "ActivityType", {k.upper().replace("-", "_"): k for k in _activity_types}, type=str
)


# handle missing values
def _missing_(cls, value):
    """Handle missing enum values by creating them on the fly"""
    # Create a new enum member with the given value
    # Convert to uppercase and replace dashes with underscores for the name
    name = str(value).upper().replace("-", "_")
    member = str.__new__(cls, value)
    member._name_ = name
    member._value_ = value
    # Add it to the enum class
    cls._value2member_map_[value] = member
    return member


ActivityType._missing_ = classmethod(_missing_)


class TimeSlot(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"


class LatLong(BaseModel):
    latitude: float
    longitude: float

class PriceRange(BaseModel):
    start_price:float
    end_price:float
    currency:str

class PlaceInfo(BaseModel):
    id: Optional[str] = None
    name: str
    location: LatLong
    types: List[str]
    photos: Optional[List] = None
    accessibility_options: Optional[Dict] = None
    opening_hours: Optional[Dict] = None
    price_range: Optional[PriceRange] = None
    price_level: Optional[str] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    international_phone_number: Optional[str] = None
    national_phone_number: Optional[str] = None
    allows_dogs: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None
    keyword_match: Optional[bool] = False

    @root_validator(pre=True)
    def handle_place_id_field(cls, values):
        """Handle both 'id' and 'place_id' fields from different sources"""
        if isinstance(values, dict):
            # If id is None or missing, try to use place_id
            if values.get('id') is None and 'place_id' in values:
                values['id'] = values['place_id']
        return values
    
    class Config:
        extra = "ignore"  # Ignore extra fields like 'place_id'


class Activity(BaseModel):
    id: int
    place: PlaceInfo
    start_time: datetime
    end_time: datetime
    activity_type: str
    duration: int  # in minutes


class Route(BaseModel):
    polylineEncoded: str
    duration: int
    distance: int


class DayItinerary(BaseModel):
    date: datetime
    morning_activities: List[Activity] = []
    afternoon_activities: List[Activity] = []
    routes: Optional[List[Route]] = None


class TripItinerary(BaseModel):
    start_date: datetime
    end_date: datetime
    days: List[DayItinerary] = []
    name:str
    is_group: bool
    price_range:Optional[PriceRange] =None
    def __str__(self):
        activies = ""
        for day in self.days:
            activies += f"Day {day.date}:\n"
            for activity in day.morning_activities:
                activies += f"  {activity.activity_type}: {activity.place.name} from {activity.start_time} to {activity.end_time}\n"
            for activity in day.afternoon_activities:
                activies += f"  {activity.activity_type}: {activity.place.name} from {activity.start_time} to {activity.end_time}\n"
        return activies

class Stop(BaseModel):
    place:PlaceInfo
    index:int
    id:str

class RoadItinerary(BaseModel):
    name:str
    stops:List[Stop]
    routes:List[Route]
    suggestions:List[PlaceInfo]
    is_group: bool

class TemplateType(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    PACKED = "packed"


def get_activity_duration(activity_type: ActivityType) -> int:
    """
    Get the duration for a specific activity type.
    Falls back to default duration if not specified.
    """
    activity_data = load_activity_types()
    durations = activity_data.get("durations", {})

    default_duration = 90

    return durations.get(str(activity_type), default_duration)
