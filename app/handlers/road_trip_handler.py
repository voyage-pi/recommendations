from typing import List,Tuple
from app.schemas.Activities import LatLong, PlaceInfo,Stop ,Route
from app.utils.distance_funcs import calculate_vector, convert_lat_long
import numpy as np
import polyline as poly
from scipy.signal import argrelextrema
from app.utils.distance_funcs import calculate_distance_lat_long, calculate_vector
import math
import uuid
import requests as request 

def calculate_division_centers(origin_cood,destination_cood,polyline)-> Tuple[List[LatLong],int,int]:
        # reduces the resolution of points of the polyline, to reduce the number of points in the route
        resolution_factor=1
        coordinates_route=poly.decode(polyline)[0:-1:resolution_factor]
        #calculate initial vector and unit
        od_vector=np.array([destination_cood.longitude-origin_cood.longitude,destination_cood.latitude-origin_cood.latitude])
        od_unit = od_vector/ np.linalg.norm(od_vector)
        num_segments=len(coordinates_route)
        segment_vectors=[]
        for i in range(math.floor(num_segments / 2)):
            segment_vectors.append(calculate_vector(coordinates_route[i],coordinates_route[i+1]))
        #break route into a list of vectors
        segment_vectors=np.array(segment_vectors)
        # calculate the dot_product of between those vectors and the origin-destination vector
        dot_products =np.vecdot(np.broadcast_to(od_vector,(segment_vectors.shape[0],2)),segment_vectors) 
        # project the dot product into the scale of the origin-destination vector 
        projections = np.expand_dims(dot_products, axis=1) * od_unit 
        # calculate the orthogonal 
        orthogonal_vectors = segment_vectors - projections# (n_points, 2)
        orthogonal_distances = np.linalg.norm(orthogonal_vectors, axis=1)  # (n_points,)
        deviation_derivative = np.gradient(orthogonal_distances)
        # First derivative peaks (fastest increasing deviation)
        second_derivative = np.gradient(deviation_derivative)
        inflection_points = argrelextrema(second_derivative, np.less)[0]
        full_distance=int(calculate_distance_lat_long(origin_cood,destination_cood))/1000 # metros 
        # subdivide the paths into the square_root of the distance in km
        num_circles=math.floor(math.sqrt(full_distance))+1
        radius=int(full_distance/num_circles)
        # to collect all the centers of the circle present on the route and 
        centers=[]
        counter=1
        for idx in inflection_points:
            # cast for future function implementation
            p=LatLong(latitude=coordinates_route[idx][0],longitude=coordinates_route[idx][1])
            # converts to km since the radius is in the same unit 
            dist_to_origin=calculate_distance_lat_long(origin_cood,p)/1000
            if dist_to_origin>=counter*radius:
                centers.append(p)
                counter+=1
        return centers, radius,num_circles

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
