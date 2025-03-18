from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime, timedelta
from pydantic import BaseModel


class ActivityType(str, Enum):
    # Google Places API main types
    AMUSEMENT_PARK = "amusement_park"
    AQUARIUM = "aquarium"
    ART_GALLERY = "art_gallery"
    BAKERY = "bakery"
    BAR = "bar"
    CAFE = "cafe"
    CASINO = "casino"
    MUSEUM = "museum"
    NIGHT_CLUB = "night_club"
    PARK = "park"
    RESTAURANT = "restaurant"
    SHOPPING_MALL = "shopping_mall"
    SPA = "spa"
    TOURIST_ATTRACTION = "tourist_attraction"
    ZOO = "zoo"


# Default durations in minutes for each activity type
ACTIVITY_DURATIONS: Dict[ActivityType, int] = {
    ActivityType.AMUSEMENT_PARK: 180,  # 3 hours
    ActivityType.AQUARIUM: 120,  # 2 hours
    ActivityType.ART_GALLERY: 90,  # 1.5 hours
    ActivityType.BAKERY: 30,  # 30 minutes
    ActivityType.BAR: 60,  # 1 hour
    ActivityType.CAFE: 45,  # 45 minutes
    ActivityType.CASINO: 120,  # 2 hours
    ActivityType.MUSEUM: 120,  # 2 hours
    ActivityType.NIGHT_CLUB: 180,  # 3 hours
    ActivityType.PARK: 90,  # 1.5 hours
    ActivityType.RESTAURANT: 90,  # 1.5 hours
    ActivityType.SHOPPING_MALL: 120,  # 2 hours
    ActivityType.SPA: 120,  # 2 hours
    ActivityType.TOURIST_ATTRACTION: 60,  # 1 hour
    ActivityType.ZOO: 180,  # 3 hours
}


class TemplateType(str, Enum):
    LIGHT = "light"
    MODERATE = "moderate"
    PACKED = "packed"


class TimeSlot(str, Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"

class PlaceInfo(BaseModel):
    id: str
    name: str
    location: Optional[Dict] = None
    types: List[str]
    photos: Optional[List] = None
    accessibility_options: Optional[Dict] = None
    opening_hours: Optional[Dict] = None
    price_range: Optional[str] = None
    rating: Optional[float] = None
    international_phone_number: Optional[str] = None
    national_phone_number: Optional[str] = None
    allows_dogs: Optional[bool] = None
    good_for_children: Optional[bool] = None
    good_for_groups: Optional[bool] = None

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
