from app.handlers.attribute_handler import questionnaire_to_attributes
from fastapi import APIRouter, HTTPException
from app.schemas.Questionnaire import TripCreate, TripResponse, TripType
from app.schemas.Activities import ActivityType, PlaceInfo, TemplateType, TripItinerary, Activity
from datetime import datetime, timedelta
from app.handlers.places_handler import (
    get_places_recommendations,
    batch_included_types_by_score,
    get_places_recommendations_batched,
)
from app.handlers.itinerary_handler import generate_itinerary, format_itinerary_response
from app.handlers.route_creation_handler import create_route_on_itinerary, get_polylines_on_places
from typing import Dict, List
from app.utils.openai_integration import OpenAIAPI
from app.schemas.GenericTypes import (
    GenericType,
    SPECIFIC_TO_GENERIC,
    GENERIC_TYPE_MAPPING,
)
import logging
import os
import json
from app.utils.redis_utils import redis_cache
from app.handlers.ranking_handler import pre_rank_places_by_category
from app.handlers.regenerate_activity_handler import regenerate_activity_handler

logger = logging.getLogger("uvicorn.error")

class PydanticJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


router = APIRouter(
    prefix="/trip",
    tags=["base"],
    responses={404: {"description": "Not found"}},
)


@router.post("/route")
async def testing_endpoint(itinerary: List[TripItinerary]):
    result = create_route_on_itinerary(itinerary)
    return {"response": result}


@router.post("/", response_model=TripResponse)
async def create_trip(trip_data: TripCreate):
    """
    Endpoint for creating a trip
    Receives a TripCreate object and returns a TripResponse object with a complete trip
    """
    trip_id = trip_data.trip_id
    trip_type= trip_data.tripType
    data = trip_data.data
    if TripType(trip_type)==TripType.PLACE or TripType(trip_type)==TripType.ZONE:

        # List[str], List[str]
        # TODO: maybe remove excluded types - seems useless
        _, _, generic_type_scores = questionnaire_to_attributes(trip_data.questionnaire)

        template_type = TemplateType.MODERATE

        # Get batches of place types, with higher-scoring types in smaller batches
        place_types_batches = batch_included_types_by_score(generic_type_scores)

        # Exclude all shopping place types
        excluded_types = (
            GENERIC_TYPE_MAPPING["shopping"]
            + GENERIC_TYPE_MAPPING["accommodation"]
            + GENERIC_TYPE_MAPPING["nightlife"]
        )

        # Get the radius based on the place name
        api_key = os.getenv("OPENAI")
        api = OpenAIAPI(api_key)

        def get_radius():
            return api.generate_radius(data.place_name) * 1000

        
        # api if trip type is place otherwise the data.radius passed  
        radius = redis_cache.get_or_set(f"radius:{data.place_name}", get_radius) if TripType(trip_type) ==TripType.PLACE else data.radius

        logger.info(f"Radius: {radius}")

        # changing the object attributtes path based on the trip type
        places: List[PlaceInfo] = await get_places_recommendations_batched(
            latitude=data.coordinates.latitude if TripType(trip_type) ==TripType.PLACE else data.center.latitude,
            longitude=data.coordinates.longitude if TripType(trip_type) ==TripType.PLACE else data.center.longitude,
            place_types_batches=place_types_batches,
            excluded_types=excluded_types,
            radius=radius,
        )

        # group places by generic type
        # {"cultural": [PlaceInfo, PlaceInfo], "outdoor": [PlaceInfo]}
        places_by_type: Dict[str, List[PlaceInfo]] = {}
        for place in places:
            added_to_types = set()
            for place_type in place.types:
                if place_type in SPECIFIC_TO_GENERIC:
                    generic_type = SPECIFIC_TO_GENERIC[place_type]
                    if generic_type not in added_to_types:
                        if generic_type not in places_by_type:
                            places_by_type[generic_type] = []
                        places_by_type[generic_type].append(place)
                        added_to_types.add(generic_type)

        # Pre-rank all places by category
        pre_ranked_places = pre_rank_places_by_category(places_by_type)

        itinerary: TripItinerary = generate_itinerary(
            places=places,
            places_by_generic_type=pre_ranked_places,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
            budget=trip_data.budget,
        )
        itinerary.name=trip_data.name
        itinerary = api.generate_itinerary(itinerary)

        # Get all used place IDs from the itinerary
        used_place_ids = set()
        for day in itinerary.days:
            for activity in day.morning_activities + day.afternoon_activities:
                used_place_ids.add(activity.place.id)

        # Filter out used places from pre-ranked places before caching
        non_used_pre_ranked_places = {
            category: [place for place in places if place.id not in used_place_ids]
            for category, places in pre_ranked_places.items()
        }

        # Store pre-ranked places in cache for future regeneration
        # Convert PlaceInfo objects to dict for JSON serialization
        pre_ranked_places_dict = {
            category: [place.dict() for place in places]
            for category, places in non_used_pre_ranked_places.items()
        }
        redis_cache.set(f"trip:{trip_id}:pre_ranked_places", json.dumps(pre_ranked_places_dict), ttl=86400)  # 24 hours

        # temporary solution | in the future generate multiple itineraries
        proposed_itineraries = [itinerary]


        routed_choosen_itinerary: TripItinerary = create_route_on_itinerary(
            proposed_itineraries
            )

        trip_response = TripResponse(
            id=trip_id,
            itinerary=routed_choosen_itinerary,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
        )

        # Cache the trip response
        trip_dict = trip_response.dict()
        redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_dict, cls=PydanticJSONEncoder), ttl=86400)  # 24 hours

        print(trip_response)

        return trip_response


@router.post("/{trip_id}/regenerate-activity")
async def regenerate_activity(trip_id: str, activity: dict):
    activity_id = activity.get("activityId")
    logger.info(f"Regenerating activity {activity_id} for trip {trip_id}")

    # get cached trip response
    cached_trip = redis_cache.get(f"trip:{trip_id}:response")
    if not cached_trip:
        raise HTTPException(status_code=404, detail="Trip not found in cache")

    trip_response = TripResponse(**json.loads(cached_trip))
    itinerary = trip_response.itinerary

    # get cached pre-ranked places
    cached_pre_ranked_places = redis_cache.get(f"trip:{trip_id}:pre_ranked_places")
    if not cached_pre_ranked_places:
        raise HTTPException(status_code=404, detail="Pre-ranked places not found in cache")

    pre_ranked_places_dict = json.loads(cached_pre_ranked_places)
    pre_ranked_places = {
        category: [PlaceInfo(**place_dict) for place_dict in places]
        for category, places in pre_ranked_places_dict.items()
    }




    new_activity = regenerate_activity_handler(trip_id, activity_id, pre_ranked_places, itinerary)


    # Update the activity in the itinerary
    for day in itinerary.days:
        for i, act in enumerate(day.morning_activities):
            if act.id == activity_id:
                day.morning_activities[i] = new_activity
                break
        for i, act in enumerate(day.afternoon_activities):
            if act.id == activity_id:
                day.afternoon_activities[i] = new_activity
                break

    # Recalculate routes for the day
    day = next(d for d in itinerary.days if any(a.id == activity_id for a in d.morning_activities + d.afternoon_activities))
    all_places = [act.place for act in day.morning_activities + day.afternoon_activities]
    polylines_duration_list = get_polylines_on_places(all_places)
    day.routes = polylines_duration_list

    # Update the cached trip response
    trip_response.itinerary = itinerary
    redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_response.dict(), cls=PydanticJSONEncoder), ttl=86400)

    return {
        "response": {
            "itinerary": itinerary
        }
    }
