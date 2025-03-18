from app.handlers.attribute_handler import questionnaire_to_attributes
from fastapi import APIRouter
from app.schemas.Questionnaire import TripCreate, TripResponse
from app.handlers.questionnaire_handler import transform_questionnaire


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
    included_types, excluded_types = questionnaire_to_attributes(trip_data.questionnaire)
    return TripResponse(id=1)
