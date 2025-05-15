import math
from typing import List
from app.schemas.Activities import LatLong, PlaceInfo
R = 6371e3

def calculate_distance_lat_long(location1:LatLong,location2:LatLong)->float:

    lat1=math.radians(location1.latitude)
    lat2=math.radians(location2.latitude)

    long1=math.radians(location1.longitude)
    long2=math.radians(location2.longitude)

    varLat = lat1- lat2
    varLong = long1 -long2

    a = math.pow(math.sin(varLat/2),2)+ math.cos(lat1) * math.cos(lat2) * math.pow(math.sin(varLong/2),2)
    c = 2 * math.atan2(math.sqrt(a),math.sqrt(1-a)) 
    d= R * c

    return d 

def calculate_distance_matrix(places:List[PlaceInfo],both=False):
    distance_matrix=[[-1.0 for i in range(len(places))] for j in range(len(places))]
    for c in range(len(places)):
        for r in range(c,len(places)):
            if r == c :
                continue
            locationR:LatLong=places[r].location
            locationC:LatLong=places[c].location
            distance_matrix[r][c]=calculate_distance_lat_long(locationC,locationR)
            if both:
                distance_matrix[c][r]=distance_matrix[r][c]

    return distance_matrix
def convert_lat_long(cood:LatLong):
    return [cood.longitude,cood.latitude] 

def calculate_vector(ar1:List[float],ar2:List[float])->List[float]:
    return [ar2[0]-ar1[0],ar2[1]-ar1[1]]
