from app.schemas.Activities import DayItinerary, DayItineraryRoute, LatLong, TripItinerary,Activity,PlaceInfo,Route
import requests as request
from typing import List,Tuple
import math 


from app.schemas.Questionnaire import Coordinates


def create_route_on_itinerary(itinerary:TripItinerary):
    days:List[DayItinerary]=itinerary.days
    new_days:List[DayItineraryRoute]=[]
    for i,d in enumerate(days):
        morning_places= [ act.place for act in d.morning_activities]
        noon_places= [act.place for act in d.afternoon_activities]
        moorning_distance= calculate_distance_matrix(morning_places) 
        noon_distance= calculate_distance_matrix(noon_places) 
        shortest_path_moorning=[morning_places[p] for p in traveling_salesman_problem(moorning_distance)]
        shortest_path_noon=[noon_places[p] for p in traveling_salesman_problem(noon_distance)]
        
        all_paths=[]
        all_paths.extend(shortest_path_moorning)
        all_paths.extend(shortest_path_noon)
        polylines_duration_list=get_polylines_on_places(all_paths) 
        acty=change_activities_sorted((d.morning_activities,d.afternoon_activities),(shortest_path_moorning,shortest_path_noon))
        print(acty)
        new_day=DayItineraryRoute(routes=polylines_duration_list,morning_activities=acty[0],afternoon_activities=acty[1],date=d.date)
        new_days.append(new_day)  
    
    return  TripItinerary(id=itinerary.id,start_date=itinerary.start_date,end_date=itinerary.end_date,days=new_days)

def change_activities_sorted(previous_activities:Tuple[List[Activity],List[Activity]],shorted_places:Tuple[List[PlaceInfo],List[PlaceInfo]])->Tuple[List[Activity],List[Activity]]:
    activities=([],[])
    aux=dict()
    for i in range(2):
        for a,c in enumerate(previous_activities[i]) :
            aux[a] = c.place
            c.place= shorted_places[i][a]
            activities[i].append(c)
    return activities

def get_polylines_on_places(places:List[PlaceInfo])->List[Route]:
    polylines=[]
    for i in range(1,len(places)):
        previous=places[i-1]
        current=places[i]
        url="http://maps-wrapper:8080/maps"
        request_body={
            "origin":previous.location.dict(),
            "destination":current.location.dict(),
            "travelMode":"WALK"
        }
        response= request.post(url,json=request_body)     
        for route in response.json()["routes"]:
            polylines.append(Route(**route))
    return polylines

def traveling_salesman_problem(matrix:List[List[float]])->List[int]:
    n = len(matrix)
    INF = float('inf')

    # Replace -1.0 with INF
    cost = [[INF if x == -1.0 else x for x in row] for row in matrix]

    dp = [[INF] * n for _ in range(1 << n)]
    parent = [[-1] * n for _ in range(1 << n)]  # to reconstruct the path

    for i in range(n):
        dp[1 << i][i] = 0

    for mask in range(1 << n):
        for u in range(n):
            if not (mask & (1 << u)):
                continue
            for v in range(n):
                if (mask & (1 << v)) or cost[u][v] == INF:
                    continue
                next_mask = mask | (1 << v)
                new_cost = dp[mask][u] + cost[u][v]
                if new_cost < dp[next_mask][v]:
                    dp[next_mask][v] = new_cost
                    parent[next_mask][v] = u  # we came to v from u

    # Find the end node with minimum cost
    full_mask = (1 << n) - 1
    min_cost = INF
    end_node = -1
    for i in range(n):
        if dp[full_mask][i] < min_cost:
            min_cost = dp[full_mask][i]
            end_node = i

    # Reconstruct path
    path = []
    mask = full_mask
    node = end_node
    while node != -1:
        path.append(node)
        prev = parent[mask][node]
        mask = mask ^ (1 << node)
        node = prev

    path.reverse()  # because we backtracked
    return path

def calculate_distance_matrix(places:List[PlaceInfo]):
    distance_matrix=[[-1.0 for i in range(len(places))] for j in range(len(places))]
    for c in range(len(places)):
        for r in range(c,len(places)):
            if r == c :
                continue
            locationR:LatLong=places[r].location
            locationC:LatLong=places[c].location
            distance_matrix[r][c]=calculate_distance_lat_long(locationC,locationR)
            distance_matrix[c][r]=distance_matrix[r][c]
    
    return distance_matrix

def calculate_distance_lat_long(location1:LatLong,location2:LatLong)->float:
    R = 6371e3

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
