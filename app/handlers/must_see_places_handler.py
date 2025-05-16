from app.schemas.Activities import LatLong, PlaceInfo
from app.schemas.Questionnaire import MustVisitPlace
from typing import List
import requests as request
from app.utils.distance_funcs import calculate_distance_lat_long

def translate_must_to_place(mvps:List[MustVisitPlace])->List[PlaceInfo]:
    places:List[PlaceInfo]=[]
    for mvp in mvps:
        try:
            url="http://place-wrapper:8080/places/"+mvp.place_id 
            response = request.get(url)
            data=response.json()
            place:PlaceInfo=PlaceInfo(**data)
            places.append(place)
        except Exception as e :
            print(f"error:{e}")
            continue
    return places

        
def validate_must_visit_places(must:List[MustVisitPlace],center:LatLong,radius_of_trip:float)-> List[PlaceInfo]:
    mvps_to_include:List[MustVisitPlace]=[]
    for mvp in must:
        dist=calculate_distance_lat_long(mvp.coordinates,center)
        if dist <=radius_of_trip:
            mvps_to_include.append(mvp)
    return translate_must_to_place(mvps_to_include) 

