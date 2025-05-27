from app.metrics import distance_metric
from app.schemas.Activities import (
    DayItinerary,
    TripItinerary,
    PlaceInfo,
    Route,
)
from app.models.scores import Score,Metric
from app.metrics.distance_metric import DistanceMetric
import requests as request
from app.utils.distance_funcs import calculate_distance_lat_long
from typing import List,Tuple


def create_route_on_itinerary(itineraries: List[TripItinerary]) -> TripItinerary:
    new_days: List[DayItinerary] = []
    # the objective is to make a weights array before array based on the responses of the forms in order to give more or less importance to certain metrics 
    weights=[1]
    metrics:List[Metric]=[DistanceMetric()]
    score=Score(list(zip(weights,metrics)))
    index_trip:int=-1
    iter_max_score:float=0.0
    iter_score:List[Tuple[TripItinerary,float]]=[]
    # iterate over all the itineraries and make a evaluation based on metrics
    for i,iter in enumerate(itineraries):
        score_value=score.calculate_full_score(iter)
        if index_trip==-1 or iter_max_score<score_value:
            iter_max_score=score_value
            index_trip=i
        iter_score.append((iter,score_value))

    choosen_itinerary:TripItinerary=itineraries[index_trip] 

    days: List[DayItinerary] = choosen_itinerary.days
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
    # appended routes to the new_days and retrieve the highest-score itinerary
    choosen_itinerary.days=new_days
    return choosen_itinerary

def get_polylines_on_places(places: List[PlaceInfo],travelMode="WALK",activate=True) -> List[Route]:
    polylines = []
    threshold=1600 # metros
    for i in range(1, len(places)):
        previous = places[i - 1]
        current = places[i]
        if calculate_distance_lat_long(previous.location,current.location) >= threshold and activate: 
            travelMode="TRASIT"
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
            "travelMode": travelMode,
        }
        response = request.post(url, json=request_body)
        for route in response.json()["routes"]:
            polylines.append(Route(**route))
    return polylines
