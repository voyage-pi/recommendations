from app.handlers.attribute_handler import questionnaire_to_attributes
from fastapi import APIRouter
from app.schemas.Questionnaire import TripCreate, TripResponse
from app.schemas.Activities import ActivityType, PlaceInfo, TemplateType, TripItinerary
from datetime import datetime, timedelta
from app.handlers.places_handler import (
    get_places_recommendations,
    batch_included_types_by_score,
    get_places_recommendations_batched,
)
from app.handlers.itinerary_handler import generate_itinerary
from app.handlers.route_creation_handler import create_route_on_itinerary
from typing import Dict, List
from app.utils.openai_integration import OpenAIAPI
from app.schemas.GenericTypes import (
    GenericType,
    SPECIFIC_TO_GENERIC,
    GENERIC_TYPE_MAPPING,
)
import logging
import os
from app.utils.redis_utils import redis_cache

logger = logging.getLogger("uvicorn.error")


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
        return api.generate_radius(trip_data.place_name) * 1000

    radius = redis_cache.get_or_set(f"radius:{trip_data.place_name}", get_radius)

    logger.info(f"Radius: {radius}")

    # Get places using the batched approach
    places: List[PlaceInfo] = await get_places_recommendations_batched(
        latitude=trip_data.coordinates.latitude,
        longitude=trip_data.coordinates.longitude,
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

    itinerary: TripItinerary = generate_itinerary(
        places=places,
        places_by_generic_type=places_by_type,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        template_type=template_type,
        generic_type_scores=generic_type_scores,
        budget=trip_data.budget,
    )

    itinerary = api.generate_itinerary(itinerary)

    # temporary solution | in the future generate multiple itineraries
    proposed_itineraries = [itinerary]

    routed_choosen_itinerary: TripItinerary = create_route_on_itinerary(
        proposed_itineraries
    )

    return TripResponse(
        id=itinerary.id,
        itinerary=routed_choosen_itinerary,
        template_type=template_type,
        generic_type_scores=generic_type_scores,
    )
