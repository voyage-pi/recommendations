from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import os


def load_activity_types():
    config_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(config_dir, "activity_types.json"), "r") as f:
        return json.load(f)


class ActivityType(str, Enum):
    """
    Enum representing different activity types.
    These values are derived from the attributes_answer.json file.
    """

    def __new__(cls, value):
        obj = str.__new__(cls, value)
        obj._value_ = value
        return obj

    @classmethod
    def _missing_(cls, value):
        # in case there are values missing
        return cls(value)


class TimeSlot(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"


class PlaceInfo(BaseModel):
    place_id: str
    name: str
    types: List[str]
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    vicinity: Optional[str] = None
    formatted_address: Optional[str] = None
    geometry: Optional[Dict] = None
    opening_hours: Optional[Dict] = None


class Activity(BaseModel):
    place: PlaceInfo
    start_time: datetime
    end_time: datetime
    activity_type: ActivityType
    duration: int  # in minutes


class DayItinerary(BaseModel):
    date: datetime
    morning_activities: List[Activity] = []
    afternoon_activities: List[Activity] = []


class TripItinerary(BaseModel):
    id: int
    start_date: datetime
    end_date: datetime
    days: List[DayItinerary] = []


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
