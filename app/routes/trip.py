from app.handlers.attribute_handler import questionnaire_to_attributes
from fastapi import APIRouter
from app.schemas.Questionnaire import TripCreate, TripResponse
from app.schemas.Activities import ActivityType, PlaceInfo, TemplateType, TripItinerary
from datetime import datetime, timedelta
from app.handlers.places_handler import get_places_recommendations
from app.handlers.itinerary_handler import generate_itinerary, format_itinerary_response
from typing import List
import logging

logger = logging.getLogger('uvicorn.error')



router = APIRouter(
    prefix="/trip",
    tags=["base"],
    responses={404: {"description": "Not found"}},
)


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


    included_activity_types: List[ActivityType] = [
        ActivityType(t) for t in included_types
    ]
    excluded_activity_types: List[ActivityType] = [
        ActivityType(t) for t in excluded_types
    ]

    start_date = datetime.now() + timedelta(days=1)

    end_date = start_date + timedelta(days=2)

    # TODO: add template selection
    template_type = TemplateType.MODERATE

    places: List[PlaceInfo] = await get_places_recommendations(
        latitude=trip_data.coordinates.latitude,
        longitude=trip_data.coordinates.longitude,
        place_types=(included_types, excluded_types),
    )

    # Generate itinerary
    itinerary: TripItinerary = generate_itinerary(
        places=places,
        included_types=included_activity_types,
        excluded_types=excluded_activity_types,
        start_date=start_date,
        end_date=end_date,
        template_type=template_type,
        generic_type_scores=generic_type_scores,
    )

    # Format response with places and their start/end times
    formatted_places = format_itinerary_response(itinerary)

    print(itinerary)

    return TripResponse(
        id=itinerary.id,
        itinerary=itinerary,
        template_type=template_type,
        generic_type_scores=generic_type_scores,
    )
