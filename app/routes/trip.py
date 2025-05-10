from app.handlers.attribute_handler import questionnaire_to_attributes
from app.utils.distance_funcs import calculate_distance_lat_long, calculate_vector
from fastapi import APIRouter, HTTPException
from app.schemas.Questionnaire import TripCreate, TripResponse, TripType
from app.schemas.Activities import LatLong, PlaceInfo, RoadItinerary, TemplateType, TripItinerary, Stop
from datetime import datetime, timedelta
from app.handlers.places_handler import (
    get_places_recommendations,
    batch_included_types_by_score,
    get_places_recommendations_batched,
)
from app.handlers.itinerary_handler import generate_itinerary, format_itinerary_response
from app.handlers.route_creation_handler import create_route_on_itinerary, get_polylines_on_places
from app.handlers.road_trip_handler import  choose_places_road, create_route_stops
from typing import Dict, List
from app.utils.openai_integration import OpenAIAPI
from app.schemas.GenericTypes import (
    GenericType,
    SPECIFIC_TO_GENERIC,
    GENERIC_TYPE_MAPPING,
)
import logging
import os
import json
from app.utils.redis_utils import redis_cache
from app.handlers.ranking_handler import pre_rank_places_by_category
from app.handlers.regenerate_activity_handler import regenerate_activity_handler
import polyline
import numpy as np
from scipy.signal import argrelextrema,find_peaks
import math
import uuid 

logger = logging.getLogger("uvicorn.error")

class PydanticJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, timedelta):
            return str(obj)
        return super().default(obj)


router = APIRouter(
    prefix="/trip",
    tags=["base"],
    responses={404: {"description": "Not found"}},
)


@router.post("/route")
async def testing_endpoint(itinerary: List[TripItinerary]):
    result = create_route_on_itinerary(itinerary)
    return {"response": result}


@router.post("/", response_model=TripResponse)
async def create_trip(trip_data: TripCreate):
    """
    Endpoint for creating a trip
    Receives a TripCreate object and returns a TripResponse object with a complete trip
    """
    trip_id = trip_data.trip_id
    trip_type= trip_data.tripType
    data = trip_data.data
    if TripType(trip_type)==TripType.PLACE or TripType(trip_type)==TripType.ZONE:

        # List[str], List[str]
        # TODO: maybe remove excluded types - seems useless
        _, _, generic_type_scores = questionnaire_to_attributes(trip_data.questionnaire)

        template_type = TemplateType.MODERATE

        # Get batches of place types, with higher-scoring types in smaller batches
        place_types_batches = batch_included_types_by_score(generic_type_scores)

        # Exclude all shopping place types
        excluded_types = (
            GENERIC_TYPE_MAPPING["shopping"]
            + GENERIC_TYPE_MAPPING["accommodation"]
            + GENERIC_TYPE_MAPPING["nightlife"]
        )

        # Get the radius based on the place name
        api_key = os.getenv("OPENAI")
        api = OpenAIAPI(api_key)

        def get_radius():
            return api.generate_radius(data.place_name) * 1000

        
        # api if trip type is place otherwise the data.radius passed  
        radius = redis_cache.get_or_set(f"radius:{data.place_name}", get_radius) if TripType(trip_type) ==TripType.PLACE else data.radius

        logger.info(f"Radius: {radius}")

        # changing the object attributtes path based on the trip type
        places: List[PlaceInfo] = await get_places_recommendations_batched(
            latitude=data.coordinates.latitude if TripType(trip_type) ==TripType.PLACE else data.center.latitude,
            longitude=data.coordinates.longitude if TripType(trip_type) ==TripType.PLACE else data.center.longitude,
            place_types_batches=place_types_batches,
            excluded_types=excluded_types,
            radius=radius,
        )

        # group places by generic type
        # {"cultural": [PlaceInfo, PlaceInfo], "outdoor": [PlaceInfo]}
        places_by_type: Dict[str, List[PlaceInfo]] = {}
        for place in places:
            added_to_types = set()
            for place_type in place.types:
                if place_type in SPECIFIC_TO_GENERIC:
                    generic_type = SPECIFIC_TO_GENERIC[place_type]
                    if generic_type not in added_to_types:
                        if generic_type not in places_by_type:
                            places_by_type[generic_type] = []
                        places_by_type[generic_type].append(place)
                        added_to_types.add(generic_type)

        # Pre-rank all places by category
        pre_ranked_places = pre_rank_places_by_category(places_by_type)

        itinerary: TripItinerary = generate_itinerary(
            places=places,
            places_by_generic_type=pre_ranked_places,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
            budget=trip_data.budget,
        )
        itinerary.name=trip_data.name
        itinerary = api.generate_itinerary(itinerary)

        # Get all used place IDs from the itinerary
        used_place_ids = set()
        for day in itinerary.days:
            for activity in day.morning_activities + day.afternoon_activities:
                used_place_ids.add(activity.place.id)

        # Filter out used places from pre-ranked places before caching
        non_used_pre_ranked_places = {
            category: [place for place in places if place.id not in used_place_ids]
            for category, places in pre_ranked_places.items()
        }

        # Store pre-ranked places in cache for future regeneration
        # Convert PlaceInfo objects to dict for JSON serialization
        pre_ranked_places_dict = {
            category: [place.dict() for place in places]
            for category, places in non_used_pre_ranked_places.items()
        }
        redis_cache.set(f"trip:{trip_id}:pre_ranked_places", json.dumps(pre_ranked_places_dict), ttl=86400)  # 24 hours

        # temporary solution | in the future generate multiple itineraries
        proposed_itineraries = [itinerary]


        routed_choosen_itinerary: TripItinerary = create_route_on_itinerary(
            proposed_itineraries
            )

        trip_response = TripResponse(
            id=trip_id,
            itinerary=routed_choosen_itinerary,
            trip_type=trip_type.value,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
        )

        # Cache the trip response
        trip_dict = trip_response.dict()
        redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_dict, cls=PydanticJSONEncoder), ttl=86400)  # 24 hours


        return trip_response

    elif TripType(trip_type)==TripType.ROAD:
        origin_cood=data.origin
        destination_cood=data.destination
        # reduces the resolution of points of the polyline, to reduce the number of points in the route
        resolution_factor=1
        coordinates_route=polyline.decode(data.polylines)[0:-1:resolution_factor]
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
        # add the origin and destiantion
        _, _, generic_type_scores = questionnaire_to_attributes(trip_data.questionnaire)

        template_type = TemplateType.MODERATE

        # Get batches of place types, with higher-scoring types in smaller batches
        place_types_batches = batch_included_types_by_score(generic_type_scores)
        
        # Exclude all shopping place types
        excluded_types = (
            GENERIC_TYPE_MAPPING["shopping"]
            + GENERIC_TYPE_MAPPING["accommodation"]
            + GENERIC_TYPE_MAPPING["nightlife"]
        )

        
        all_places:List[List[PlaceInfo]]=[]
        for i in centers:
            try:
                places: List[PlaceInfo] = await get_places_recommendations_batched(
                    latitude=i.latitude,
                    longitude=i.longitude,
                    place_types_batches=place_types_batches,
                    excluded_types=excluded_types,
                    radius=radius*1000,
                )
                all_places.append(places)
            except Exception as e:
                # não recebeu nenhum local
                print(e)
                continue
    
        centers.insert(0,origin_cood)
        centers.append(destination_cood)

        stops:List[Stop]=choose_places_road(all_places,centers) 
        origin_place=PlaceInfo(name="origin",location=dict(data.origin),types=[]) 
        destination_place=PlaceInfo(name="destination",location=dict(data.destination),types=[])
        stops.insert(0,Stop(id=str(uuid.uuid4()),index=0,place=origin_place)) 
        stops.append(Stop(id=str(uuid.uuid4()),index=len(stops),place=destination_place)) 
        routes= create_route_stops(stops)
        road:RoadItinerary= RoadItinerary(name=trip_data.name,routes=routes,stops=stops,suggestions=[])
        response=TripResponse(itinerary=road,generic_type_scores=generic_type_scores,trip_type="road",template_type="moderate")
        return response 
        

@router.post("/{trip_id}/regenerate-activity")
async def regenerate_activity(trip_id: str, activity: dict):
    activity_id = activity.get("activityId")
    logger.info(f"Regenerating activity {activity_id} for trip {trip_id}")

    # get cached trip response
    cached_trip = redis_cache.get(f"trip:{trip_id}:response")
    if not cached_trip:
        raise HTTPException(status_code=404, detail="Trip not found in cache")

    trip_response = TripResponse(**json.loads(cached_trip))
    itinerary = trip_response.itinerary

    # get cached pre-ranked places
    cached_pre_ranked_places = redis_cache.get(f"trip:{trip_id}:pre_ranked_places")
    if not cached_pre_ranked_places:
        raise HTTPException(status_code=404, detail="Pre-ranked places not found in cache")

    pre_ranked_places_dict = json.loads(cached_pre_ranked_places)
    pre_ranked_places = {
        category: [PlaceInfo(**place_dict) for place_dict in places]
        for category, places in pre_ranked_places_dict.items()
    }




    new_activity = regenerate_activity_handler(trip_id, activity_id, pre_ranked_places, itinerary)


    # Update the activity in the itinerary
    for day in itinerary.days:
        for i, act in enumerate(day.morning_activities):
            if act.id == activity_id:
                day.morning_activities[i] = new_activity
                break
        for i, act in enumerate(day.afternoon_activities):
            if act.id == activity_id:
                day.afternoon_activities[i] = new_activity
                break

    # Recalculate routes for the day
    day = next(d for d in itinerary.days if any(a.id == activity_id for a in d.morning_activities + d.afternoon_activities))
    all_places = [act.place for act in day.morning_activities + day.afternoon_activities]
    polylines_duration_list = get_polylines_on_places(all_places)
    day.routes = polylines_duration_list

    # Update the cached trip response
    trip_response.itinerary = itinerary
    redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_response.dict(), cls=PydanticJSONEncoder), ttl=86400)

    return {
        "response": {
            "itinerary": itinerary
        }
    }
