from typing import List
from app.schemas.Activities import PlaceInfo


async def get_places_recommendations(
    latitude: float,
    longitude: float,
    place_types: List[str],
    radius: int = 5000,  # 5km radius
    max_results: int = 20,
) -> List[PlaceInfo]:
    """
    Get place recommendations from Google Places API or another service
    This is a placeholder for your actual service wrapper implementation
    """
    sample_places = [
        PlaceInfo(
            place_id=f"place_{i}",
            name=f"Sample Place {i}",
            types=[place_type] if i < len(place_types) else ["tourist_attraction"],
            rating=4.5,
            vicinity=f"Sample Address {i}",
            geometry={"location": {"lat": latitude, "lng": longitude}},
        )
        for i in range(max_results)
        for place_type in (
            place_types[:1] if i < len(place_types) else ["tourist_attraction"]
        )
    ]

    return sample_places[:max_results]
