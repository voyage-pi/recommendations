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
    radius: int = 10000, 
    max_results: int = 20,
) -> List[PlaceInfo]:
    """
    Get place recommendations from Google Places API or another service
    This is a placeholder for your actual service wrapper implementation
    """

    included_types = place_types[0]
    print(f"Included types: {included_types}")
    excluded_types = place_types[1]
    print(f"Excluded types: {excluded_types}")
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
                user_ratings_total=data.get("userRatingCount"),
                international_phone_number=data.get("internationalPhoneNumber"),
                national_phone_number=data.get("nationalPhoneNumber"),
                allows_dogs=data.get("allowsDogs"),
                good_for_children=data.get("goodForChildren"),
                good_for_groups=data.get("goodForGroups"),
            )
            places.append(place)
        return places
    else:
        logging.debug(f"Response status: {status}")
        response_text = response.text
        raise Exception(f"Error response from place-wrapper: {response_text}")

async def get_places_recommendations_batched(
    latitude: float,
    longitude: float,
    place_types_batches: List[List[str]],
    excluded_types: List[str] = [],
    radius: int = 5000,  # 5km radius
    max_results: int = 20,
) -> List[PlaceInfo]:
    """
    Get place recommendations by making multiple API requests with batches of place types.
    Each batch contains at most 50 types, with higher-priority types in smaller batches.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        place_types_batches: List of batches, where each batch is a list of place types
        excluded_types: List of place types to exclude
        radius: Search radius in meters
        max_results: Maximum number of results to return per batch
        
    Returns:
        Combined list of place recommendations from all batches
    """
    all_places: List[PlaceInfo] = []
    seen_place_ids = set()

    logger.info(f"Included types: {place_types_batches}")
    logger.info(f"Excluded types: {excluded_types}")
    
    logger.info(f"Making requests for {len(place_types_batches)} batches of place types")
    
    for i, batch in enumerate(place_types_batches):
        logger.info(f"Processing batch {i+1} with {len(batch)} place types")
        
        batch_places = await get_places_recommendations(
            latitude=latitude,
            longitude=longitude,
            place_types=(batch, excluded_types),
            radius=radius,
            max_results=max_results
        )
        
        logger.info(f"Batch {i+1} returned {len(batch_places)} places")
        
        # Add only unique places to the result
        for place in batch_places:
            if place.id not in seen_place_ids:
                all_places.append(place)
                seen_place_ids.add(place.id)
    
    logger.info(f"Total unique places found across all batches: {len(all_places)}")
    return all_places


def batch_included_types_by_score(generic_types_score) -> List[List[str]]:
    """
    Splits all place types into multiple batches of at most 50 types per batch.
    Higher-scoring generic types get placed in smaller batches for more focused searches.
    Always creates at least two batches even if total types are less than 50.
    
    Args:
        generic_types_score: Dictionary mapping generic type to its score
        
    Returns:
        List of batches, where each batch is a list of specific place types
    """
    logger.info(f"Generic types score: {generic_types_score}")
    # Remove landmarks from generic types score as it's only used for scoring
    generic_types_score = {k: v for k, v in generic_types_score.items() if k != "landmarks"}
    
    # Sort generic types by score in descending order
    sorted_types = sorted(generic_types_score.items(), key=lambda x: x[1], reverse=True)
    
    MAX_BATCH_SIZE = 50
    
    # First, calculate the total number of types
    total_types = sum(len(GENERIC_TYPE_MAPPING[generic_type]) for generic_type, _ in sorted_types)
    
    # Calculate the optimal number of batches needed, but ensure at least 2 batches
    num_batches = max(2, (total_types + MAX_BATCH_SIZE - 1) // MAX_BATCH_SIZE)
    
    # Initialize batches
    batches = [[] for _ in range(num_batches)]
    batch_counts = [0] * num_batches
    
    # If we have fewer types than would normally require 2 batches, 
    # we'll distribute them to ensure the higher priority types are in the first batch
    if total_types <= MAX_BATCH_SIZE:
        first_batch_size = total_types // 2
        current_count = 0
        batch_idx = 0
        
        for generic_type, score in sorted_types:
            specific_types = GENERIC_TYPE_MAPPING[generic_type]
            for type_name in specific_types:
                batches[batch_idx].append(type_name)
                current_count += 1
                
                # Move to second batch after we've filled half of the types in the first batch
                if batch_idx == 0 and current_count >= first_batch_size:
                    batch_idx = 1
    else:
        # For larger sets, distribute types across batches, prioritizing higher scored generic types
        for generic_type, score in sorted_types:
            specific_types = GENERIC_TYPE_MAPPING[generic_type]
            types_to_allocate = specific_types.copy()
            
            if not types_to_allocate:
                continue
                
            # For higher scored types, allocate to batches with fewer types first
            while types_to_allocate:
                # Find the batch with the smallest current count
                min_batch_idx = batch_counts.index(min(batch_counts))
                
                # Calculate how many types to add to this batch
                space_left = MAX_BATCH_SIZE - batch_counts[min_batch_idx]
                types_to_add = min(len(types_to_allocate), space_left)
                
                if types_to_add <= 0:
                    # All batches are full
                    break
                    
                # Add types to this batch
                batches[min_batch_idx].extend(types_to_allocate[:types_to_add])
                batch_counts[min_batch_idx] += types_to_add
                
                # Remove allocated types
                types_to_allocate = types_to_allocate[types_to_add:]
    
    # Remove any empty batches
    batches = [batch for batch in batches if batch]
    
    # Log the batch sizes for debugging
    for i, batch in enumerate(batches):
        logger.info(f"Batch {i+1} contains {len(batch)} types")
    
    return batches
