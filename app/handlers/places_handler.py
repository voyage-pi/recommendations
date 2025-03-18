from typing import List, Tuple
from app.schemas.Activities import PlaceInfo
import requests as request

async def get_places_recommendations(
    latitude: float,
    longitude: float,
    place_types: Tuple[List[str],List[str]],
    radius: int = 5000,  # 5km radius
    max_results: int = 20,
) -> List[PlaceInfo]:
    """
    Get place recommendations from Google Places API or another service
    This is a placeholder for your actual service wrapper implementation
    """
    included_types=place_types[0]
    excluded_types=place_types[1]
    url="localhost:"
    request_body={
        "location":{
            "latitude":latitude,
            "longitude":longitude,
        },
        "radius":radius,
        "includedTypes":included_types,
        "excludedTypes":excluded_types,
    }

    response= request.get(url,json=request_body)     
    r=response.json()
    places=r.get("places")
    # not tested, idk if is able to make the cast
    new_places=[PlaceInfo(**obj) for obj in places]

    return new_places
