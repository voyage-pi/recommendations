from typing import List
from fastapi import HTTPException
from app.schemas.Activities import Activity
from app.utils.redis_utils import redis_cache
from app.schemas.GenericTypes import SPECIFIC_TO_GENERIC
import json
from app.schemas.Questionnaire import TripItinerary
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("uvicorn.error")

class PydanticJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)

def regenerate_activity_handler(trip_id: str, activity_id: int, places: dict, itinerary: List[TripItinerary]):
    def get_current_activity():
        for day in itinerary.days:
            for act in day.morning_activities + day.afternoon_activities:
                if act.id == activity_id:
                    return act
        return None

    def get_activity_type(place):
        for place_type in place.types:
            if place_type in SPECIFIC_TO_GENERIC:
                return SPECIFIC_TO_GENERIC[place_type]
        return None

    def get_used_place_ids():
        used_ids = set()
        for day in itinerary.days:
            for act in day.morning_activities + day.afternoon_activities:
                used_ids.add(act.place.id)
        return used_ids

    def find_new_place(current_type, used_ids):
        if current_type not in places:
            return None

        type_places = places[current_type]
        available_places = [p for p in type_places if p.id not in used_ids]

        
        if available_places:
            return available_places[0]

        for category in places.keys():
            if category == current_type:
                continue
            available_places = [p for p in places[category] if p.id not in used_ids]
            if available_places:
                return available_places[0]
        return None

    def update_place_queue(current_place, current_type):
        if current_type in places and current_place in places[current_type]:
            type_places = places[current_type]
            type_places.remove(current_place)
            type_places.append(current_place)
            places_dict = {
                category: [place.dict() for place in places]
                for category, places in places.items()
            }
            redis_cache.set(f"trip:{trip_id}:pre_ranked_places", json.dumps(places_dict, cls=PydanticJSONEncoder), ttl=604800)

    current_activity = get_current_activity()
    if not current_activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    current_type = get_activity_type(current_activity.place)
    if not current_type:
        raise HTTPException(status_code=400, detail="Could not determine activity type")

    used_place_ids = get_used_place_ids()
    new_place = find_new_place(current_type, used_place_ids)

    if not new_place:
        raise HTTPException(status_code=400, detail="No alternative places available")

    update_place_queue(current_activity.place, current_type)

    return Activity(
        id=current_activity.id,
        place=new_place,
        start_time=current_activity.start_time,
        end_time=current_activity.end_time,
        activity_type=current_activity.activity_type,
        duration=current_activity.duration,
    )
    