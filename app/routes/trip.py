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
    positive_tags, negative_tags = transform_questionnaire(trip_data.questionnaire)
    return {"positive_tags": positive_tags, "negative_tags": negative_tags}
