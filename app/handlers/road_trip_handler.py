from typing import List
from app.schemas.Activities import LatLong, PlaceInfo,Stop ,Route
from app.schemas.Questionnaire import Place
from app.utils.distance_funcs import calculate_vector, convert_lat_long
import numpy as np
import math
import uuid
import requests as request 

def choose_places_road(all_places:List[List[PlaceInfo]],centers :List[LatLong])->List[Stop]:
    vector_centers=[]  
    for i in range(len(centers)-1):
        vector_centers.append(calculate_vector([centers[i].longitude,centers[i].latitude],[centers[i+1].longitude,centers[i+1].latitude]))

    sub_vectors=[]
    for c in range(len(centers)-2):# number of circles without the origin and destination
        origin=centers[c]
        sub_vectors.append([])
        for i in range(len(all_places[c])):# make vectors between the previous center and each place of each zone
            dest=all_places[c][i].location
            sub_vectors[c].append(calculate_vector(convert_lat_long(origin),convert_lat_long(dest)))

    # calculate the dotproduct between each zone place and the vectors between the centers
    dots=[]
    for i in range(len(sub_vectors)):
        places_vectors=sub_vectors[i]
        dots.append([])
        for p in range(len(places_vectors)):
            dots[i].append(np.dot(vector_centers[i],places_vectors[p]))

    n=math.ceil(math.sqrt(len(centers)-2))-1
    top_n_indices = [np.argsort(sublist)[-n:][::-1] for sublist in dots]
    places_to_visit:List[Stop]=[Stop(place=all_places[i][idx],id=str(uuid.uuid4()),index=i+1) for i, p in enumerate(top_n_indices) for idx in p]
    # create a the road trip on a single day on the moorning activities for structure simplicity 
    return places_to_visit

def  create_route_stops(stops:List[Stop])->List[Route]:
    # order the stops by index (order of passage)
    stops.sort(key=lambda s: s.index)
    polylines=[]
    for i in range(1, len(stops)):
        previous = stops[i - 1].place
        current = stops[i].place
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
            "travelMode": "VEHICLE",
        }
        response = request.post(url, json=request_body)
        for route in response.json()["routes"]:
            polylines.append(Route(**route))
    return polylines
