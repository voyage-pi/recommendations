from app.schemas.Activities import LatLong, PlaceInfo
from typing import List
import requests as request
from app.utils.distance_funcs import calculate_distance_lat_long

def validate_must_visit_places(must:List[PlaceInfo],center:LatLong,radius_of_trip:float)-> List[PlaceInfo]:
    mvps_to_include:List[PlaceInfo]=[]
    for mvp in must:
        dist=calculate_distance_lat_long(mvp.location,center)
        if dist <=radius_of_trip:
            mvps_to_include.append(mvp)
    return mvps_to_include 

