from app.schemas.Activities import DayItinerary, LatLong, TripItinerary,Activity,PlaceInfo
import requests as request
from typing import List
import math 


from app.schemas.Questionnaire import Coordinates


def create_route_on_itinerary(itinerary:TripItinerary):
    days:List[DayItinerary]=itinerary.days
    for d in days:
        orderOfPlaces:PlaceInfo=[]
        morning_places= [ act.place for act in d.morning_activities]
        noon_places= [act.place for act in d.afternoon_activities]
        moorning_distance= calculate_distance_matrix(morning_places) 
        noon_distance= calculate_distance_matrix(noon_places) 
        total_distances=calculate_distance_matrix(morning_places.extend(noon_places))
        

def get_polylines_on_activities(activities:List[Activity]):
    for i in range(1,len(activities)):
        url="http://maps-wrapper:8080/routes"
        request_body={

        }
        response= request.post(url,json=request_body)     
        status = response.status_code

def calculate_distance_matrix(places:List[PlaceInfo]):
    distance_matrix=[[-1.0 for i in range(len(places))] for j in range(len(places))]
    for c in range(len(places)):
        for r in range(len(places)):
            if r == c or distance_matrix[r][c]!=distance_matrix[r][c] :
                continue
            locationR:LatLong=places[r].location
            locationC:LatLong=places[c].location
            distance_matrix[r][c]=calculate_distance_lat_long(locationC,locationR)

    return distance_matrix

def calculate_distance_lat_long(location1:LatLong,location2:LatLong)->float:
    R = 6371e3

    lat1=location1.latitude
    lat2=location2.latitude

    long1=location1.longitude
    long2=location2.longitude

    varLat = lat1- lat2
    varLong = long1 -long2

    a = math.pow(math.sin(varLat/2),2)+ math.cos(lat1) * math.cos(lat2) * math.pow(math.sin(varLong/2),2)
    c = 2 * math.atan2(math.sqrt(a),math.sqrt(1-a)) 
    d= R * c

    return d 
