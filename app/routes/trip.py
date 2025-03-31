from app.handlers.attribute_handler import questionnaire_to_attributes
from fastapi import APIRouter
from app.schemas.Questionnaire import TripCreate, TripResponse
from app.schemas.Activities import ActivityType, PlaceInfo, TemplateType, TripItinerary
from datetime import datetime, timedelta
from app.handlers.places_handler import get_places_recommendations
from app.handlers.itinerary_handler import generate_itinerary, format_itinerary_response
from app.handlers.route_creation_handler import create_route_on_itinerary
from typing import Dict, List

from app.schemas.GenericTypes import GenericType, SPECIFIC_TO_GENERIC
import logging

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
    included_types, excluded_types, generic_type_scores = questionnaire_to_attributes(
        trip_data.questionnaire
    )

    # get included and excluded activity types
    included_activity_types: List[ActivityType] = [
        ActivityType(t) for t in included_types
    ]
    excluded_activity_types: List[ActivityType] = [
        ActivityType(t) for t in excluded_types
    ]

    # TODO: add template selection
    template_type = TemplateType.MODERATE

    places: List[PlaceInfo] = await get_places_recommendations(
        latitude=trip_data.coordinates.latitude,
        longitude=trip_data.coordinates.longitude,
        place_types=(included_types, excluded_types),
    )

    # group places by generic type
    # {"cultural": [PlaceInfo, PlaceInfo], "outdoor": [PlaceInfo]}
    places_by_type: Dict[str, List[PlaceInfo]] = {}
    for place in places:
        for place_type in place.types:
            if place_type in SPECIFIC_TO_GENERIC:
                generic_type = SPECIFIC_TO_GENERIC[place_type]
                if generic_type not in places_by_type:
                    places_by_type[generic_type] = []
                places_by_type[generic_type].append(place)

    itinerary: TripItinerary = generate_itinerary(
        places=places,
        places_by_generic_type=places_by_type,
        start_date=trip_data.start_date,
        end_date=trip_data.end_date,
        template_type=template_type,
        generic_type_scores=generic_type_scores,
        budget=trip_data.budget,
    )

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
