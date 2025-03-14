from fastapi import APIRouter

router = APIRouter(
    prefix="/trip",
    tags=["base"],
    responses={404: {"description": "Not found"}},
)


@router.post("/")
async def create_trip():
    return {"Hello": "World!"}
