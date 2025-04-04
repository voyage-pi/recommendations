from typing import List, Tuple
from app.schemas.Activities import PlaceInfo
from app.schemas.GenericTypes import GENERIC_TYPE_MAPPING
import requests as request
import logging
import math
logger = logging.getLogger("uvicorn.error")


async def get_places_recommendations(
    latitude: float,
    longitude: float,
    place_types: Tuple[List[str], List[str]],
    radius: int = 5000,  # 5km radius
    max_results: int = 20,
) -> List[PlaceInfo]:
    """
    Get place recommendations from Google Places API or another service
    This is a placeholder for your actual service wrapper implementation
    """

    included_types = place_types[0]
    excluded_types = place_types[1]
    url = "http://place-wrapper:8080/places/"

    request_body = {
        "location": {
            "latitude": latitude,
            "longitude": longitude,
        },
        "radius": radius,
        "includedTypes": included_types,
        "excludedTypes": excluded_types,
    }
    response = request.post(url, json=request_body)
    status = response.status_code
    if status == 200:
        responseBody = response.json()
        places_google = responseBody.get("places")
        places: List[PlaceInfo] = []
        for data in places_google:
            place = PlaceInfo(
                id=data.get("ID"),
                name=data.get("name"),
                location=data.get("location"),
                types=data.get("types", []),
                photos=data.get("photos", []),
                accessibility_options=data.get("accessibilityOptions", {}),
                opening_hours=data.get("OpeningHours", {}),
                price_range=data.get("priceRange"),
                rating=data.get("rating"),
                international_phone_number=data.get("internationalPhoneNumber"),
                national_phone_number=data.get("nationalPhoneNumber"),
                allows_dogs=data.get("allowsDogs"),
                good_for_children=data.get("goodForChildren"),
                good_for_groups=data.get("goodForGroups"),
            )
            places.append(place)
        return places
    else:
        logging.debug(f"Response status:{status}")
        logging.debug(f"Response:{response}")
        return []

def filter_included_types_by_score(generic_types_score)->List[str]:
    total_score=sum([v  for k,v in generic_types_score.items()]) 
    LIMIT_TYPES=50
    percentage_of_generic_type={k:v/total_score for k,v in generic_types_score.items()}
    new_included=[]
    new_excluded=[]
    for k,v in percentage_of_generic_type.items():
        n=math.ceil(v*LIMIT_TYPES)
        types_n=len(GENERIC_TYPE_MAPPING[k])
        number_of_specific_types= n if n <= types_n  else types_n
        new_included.extend(GENERIC_TYPE_MAPPING[k][:number_of_specific_types]) 
    return new_included
