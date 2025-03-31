from app.schemas.Activities import (
    DayItinerary,
    TripItinerary,
    PlaceInfo,
    Route,
)
import requests as request
from typing import List


def create_route_on_itinerary(itineraries: List[TripItinerary]) -> TripItinerary:
    choosen_routed_itinerary = None
    for iter in itineraries:
        days: List[DayItinerary] = iter.days
        new_days: List[DayItinerary] = []
        for i, d in enumerate(days):
            morning_places = [act.place for act in d.morning_activities]
            noon_places = [act.place for act in d.afternoon_activities]
            all_paths = []
            all_paths.extend(morning_places)
            all_paths.extend(noon_places)
            polylines_duration_list = get_polylines_on_places(all_paths)
            new_day = DayItinerary(
                routes=polylines_duration_list,
                morning_activities=d.morning_activities,
                afternoon_activities=d.afternoon_activities,
                date=d.date,
            )
            new_days.append(new_day)
        # here for future work make a system of ranking metrics to evaluate given itineraries
        choosen_routed_itinerary = TripItinerary(
            id=iter.id,
            start_date=iter.start_date,
            end_date=iter.end_date,
            days=new_days,
        )

    assert choosen_routed_itinerary is not None
    return choosen_routed_itinerary


def get_polylines_on_places(places: List[PlaceInfo]) -> List[Route]:
    polylines = []
    for i in range(1, len(places)):
        previous = places[i - 1]
        current = places[i]
        url = "http://maps-wrapper:8080/maps"
        request_body = {
            "origin": (
                previous.location.dict()
                if not previous.id
                else {"place_id": previous.id}
            ),
            "destination": (
                current.location.dict() if not current.id else {"place_id": current.id}
            ),
            "travelMode": "WALK",
        }
        response = request.post(url, json=request_body)
        for route in response.json()["routes"]:
            print(f"Route {route}")
            polylines.append(Route(**route))
    return polylines
