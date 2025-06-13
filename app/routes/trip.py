from app.handlers.attribute_handler import questionnaire_to_attributes
from app.handlers.must_see_places_handler import validate_must_visit_places
from fastapi import APIRouter, HTTPException
from app.schemas.Questionnaire import TripCreate, TripResponse, TripType
from app.schemas.Activities import LatLong, PlaceInfo, PriceRange, RoadItinerary, TemplateType, TripItinerary, Stop
from datetime import datetime, timedelta
from app.handlers.places_handler import (
    get_places_recommendations,
    batch_included_types_by_score,
    get_places_recommendations_batched,
    search_places_by_keyword,
)
from app.handlers.itinerary_handler import generate_itinerary 
from app.handlers.route_creation_handler import create_route_on_itinerary, get_polylines_on_places
from app.handlers.road_trip_handler import  choose_places_road, create_route_stops,calculate_division_centers
from app.handlers.budget_handler import place_price, fit_places_on_price
from typing import Dict, List,Tuple
from app.utils.openai_integration import OpenAIAPI
from app.schemas.GenericTypes import (
    GenericType,
    SPECIFIC_TO_GENERIC,
    GENERIC_TYPE_MAPPING,
)
import logging
import os
import json
import requests
from app.utils.redis_utils import redis_cache
from app.handlers.ranking_handler import pre_rank_places_by_category
from app.handlers.regenerate_activity_handler import regenerate_activity_handler
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
        must_places:List[PlaceInfo] | None =  trip_data.must_visit_places if "must_visit_places" in trip_data.model_dump() else None


        # Get latitude and longitude based on trip type
        latitude = data.coordinates.latitude if TripType(trip_type) == TripType.PLACE else data.center.latitude
        longitude = data.coordinates.longitude if TripType(trip_type) == TripType.PLACE else data.center.longitude
        # Get places from recommendation service
        places: List[PlaceInfo] = await get_places_recommendations_batched(
            latitude=latitude,
            longitude=longitude,
            place_types_batches=place_types_batches,
            excluded_types=excluded_types,
            radius=radius,
        )

        # If keywords were provided, search for places by keywords
        keyword_places: List[PlaceInfo] = []
        if trip_data.keywords and len(trip_data.keywords) > 0:
            logger.info(f"Searching for places with {len(trip_data.keywords)} keywords")
            
            # Get the place name from trip data
            place_name = data.place_name if TripType(trip_type) == TripType.PLACE else "this area"
            
            # Search for each keyword
            for keyword in trip_data.keywords:
                try:
                    keyword_results = await search_places_by_keyword(
                        keyword=keyword,
                        place_name=place_name,
                        latitude=latitude,
                        longitude=longitude,
                        radius=radius
                    )
                    
                    if keyword_results:
                        logger.info(f"Found {len(keyword_results)} places for keyword '{keyword}'")
                        keyword_places.extend(keyword_results)
                except Exception as e:
                    logger.error(f"Error searching for keyword '{keyword}': {str(e)}")
            
            # Deduplicate places by ID
            seen_ids = set()
            unique_keyword_places = []
            
            for place in keyword_places:
                if place.id not in seen_ids:
                    seen_ids.add(place.id)
                    unique_keyword_places.append(place)
            
            logger.info(f"Found {len(unique_keyword_places)} unique places from keywords search")
            
            # Add keyword places to regular places
            # We'll also mark these places as coming from a keyword search
            for place in unique_keyword_places:
                if place.id not in [p.id for p in places]:
                    places.append(place)

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
        # get must visit places info then generate the itinerary with them
        mvps:List[PlaceInfo]=[] 
        if must_places is not None:
            mvps.extend(validate_must_visit_places(must_places,LatLong(latitude=latitude,longitude=longitude),radius))

        for_r=places
        for_r.extend(mvps)
        # Parse strings to datetime objects

        # Calculate and associate price differences 
        prices:List[Tuple[PlaceInfo,PriceRange]]=place_price(for_r)
        # Select the places to be inside the budget
        new_places,total_range=fit_places_on_price(prices,int(trip_data.budget))

        itinerary: TripItinerary = generate_itinerary(
            places=new_places,
            places_by_generic_type=pre_ranked_places,
            start_date=trip_data.start_date,
            end_date=trip_data.end_date,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
            must_visit_places=mvps,
            is_group=trip_data.is_group,
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
        redis_cache.set(f"trip:{trip_id}:pre_ranked_places", json.dumps(pre_ranked_places_dict), ttl=604800)  # 7 days

        #add price-range to itinerary
        itinerary.price_range=total_range
        # temporary solution | in the future generate multiple itineraries
        proposed_itineraries = [itinerary]


        routed_choosen_itinerary: TripItinerary = create_route_on_itinerary(
            proposed_itineraries
            )

        trip_response = TripResponse(
            id=trip_id,
            itinerary=routed_choosen_itinerary,
            type=trip_type.value,
            trip_type=trip_type.value,
            template_type=template_type,
            generic_type_scores=generic_type_scores,
            is_group=trip_data.is_group,
        )

        # Update the cached trip response
        trip_response.itinerary = itinerary
        
        # Ensure all required fields are set before saving
        if not hasattr(trip_response, 'trip_type') or not trip_response.trip_type:
            trip_response.trip_type = "place"  # Default to place if missing
        
        if not hasattr(trip_response, 'template_type') or not trip_response.template_type:
            trip_response.template_type = TemplateType.MODERATE
        
        
        if not hasattr(trip_response, 'id') or not trip_response.id:
            trip_response.id = trip_id
        
        # Convert to dict and save to cache
        trip_dict = trip_response.dict()
        redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_dict, cls=PydanticJSONEncoder), ttl=604800)

        return trip_response

    elif TripType(trip_type)==TripType.ROAD:
        try:
            # Ensure required fields are present
            if not hasattr(data, 'origin') or not hasattr(data, 'destination') or not hasattr(data, 'polylines'):
                raise HTTPException(
                    status_code=400, 
                    detail="Road trip requires origin, destination, and polylines fields"
                )
                
            origin_place=data.origin
            dest_place=data.destination
            origin_cood=origin_place.location
            destination_cood=dest_place.location
            centers,radius,_ = calculate_division_centers(origin_cood,destination_cood,data.polylines)
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
                    logger.error(f"Error getting places: {str(e)}")
                    continue
        
            centers.insert(0,origin_cood)
            centers.append(destination_cood)

            stops:List[Stop]=choose_places_road(all_places,centers) 
            stops.insert(0,Stop(id=str(uuid.uuid4()),index=0,place=origin_place)) 
            stops.append(Stop(id=str(uuid.uuid4()),index=len(stops),place=dest_place)) 
            routes= create_route_stops(stops)
            road:RoadItinerary= RoadItinerary(
                name=trip_data.name,
                routes=routes,
                stops=stops,
                suggestions=[],
                is_group=trip_data.is_group
            )
            
            response=TripResponse(
                itinerary=road,
                generic_type_scores=generic_type_scores,
                trip_type="road",
                template_type=template_type,
                id=trip_id,
                is_group=trip_data.is_group
            )
            return response
        except Exception as e:
            logger.error(f"Error creating road trip: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to create road trip: {str(e)}")


@router.post("/{trip_id}/regenerate-activity")
async def regenerate_activity(trip_id: str, activity: dict):
    activity_id = activity.get("activityId")
    logger.info(f"Regenerating activity {activity_id} for trip {trip_id}")

    # get cached trip response
    cached_trip = redis_cache.get(f"trip:{trip_id}:response")
    if not cached_trip:
        raise HTTPException(status_code=404, detail="Trip not found in cache")

    try:
        cached_data = json.loads(cached_trip)
        # Ensure required fields exist
        if "trip_type" not in cached_data:
            cached_data["trip_type"] = "place"  # Default to place if missing
            
        if "template_type" not in cached_data:
            cached_data["template_type"] = "moderate"
            
        if "id" not in cached_data:
            cached_data["id"] = trip_id
            
        if "is_group" not in cached_data:
            cached_data["is_group"] = False
        
        trip_response = TripResponse(**cached_data)
        itinerary = trip_response.itinerary
    except Exception as e:
        logger.error(f"Error loading cached trip data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid trip data in cache: {str(e)}")

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
    print(new_activity.place.name)

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
    
    # Ensure all required fields are set before saving
    if not hasattr(trip_response, 'trip_type') or not trip_response.trip_type:
        trip_response.trip_type = "place"  # Default to place if missing
        
    if not hasattr(trip_response, 'template_type') or not trip_response.template_type:
        trip_response.template_type = TemplateType.MODERATE
    
    
    if not hasattr(trip_response, 'id') or not trip_response.id:
        trip_response.id = trip_id
    
    # Convert to dict and save to cache
    trip_dict = trip_response.dict()
    redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_dict, cls=PydanticJSONEncoder), ttl=604800)

    return {
        "response": {
            "itinerary": itinerary
        }
    }
    

@router.delete("/{trip_id}/delete-activity/{activity_id}")
async def delete_activity(trip_id: str, activity_id: str):
    logger.info(f"Deleting activity {activity_id} for trip {trip_id}")

    # get cached trip response
    cached_trip = redis_cache.get(f"trip:{trip_id}:response")
    if not cached_trip:
        raise HTTPException(status_code=404, detail="Trip not found in cache")

    try:
        cached_data = json.loads(cached_trip)
        # Ensure required fields exist
        if "trip_type" not in cached_data:
            cached_data["trip_type"] = "place"  # Default to place if missing
        
        if "template_type" not in cached_data:
            cached_data["template_type"] = "moderate"
            
        if "id" not in cached_data:
            cached_data["id"] = trip_id
            
        if "is_group" not in cached_data:
            cached_data["is_group"] = False
        
        trip_response = TripResponse(**cached_data)
        itinerary = trip_response.itinerary
    except Exception as e:
        logger.error(f"Error loading cached trip data: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid trip data in cache: {str(e)}")

    # Debug: Log all activity IDs to identify issues
    all_ids = []
    for day in itinerary.days:
        for act in day.morning_activities:
            all_ids.append(f"morning: {act.id} (type: {type(act.id).__name__})")
        for act in day.afternoon_activities:
            all_ids.append(f"afternoon: {act.id} (type: {type(act.id).__name__})")
    
    logger.info(f"Available activity IDs: {all_ids}")
    logger.info(f"Looking for activity ID: {activity_id} (type: {type(activity_id).__name__})")

    # Find and remove the activity from the itinerary
    activity_found = False
    affected_day = None
    
    for day in itinerary.days:
        # Check morning activities
        for i, act in enumerate(day.morning_activities):
            # Try different comparisons to handle potential type mismatches
            if str(act.id) == str(activity_id):
                logger.info(f"Found activity {activity_id} in morning activities")
                activity_found = True
                affected_day = day
                day.morning_activities.pop(i)
                break
        
        if activity_found:
            break
            
        # Check afternoon activities
        for i, act in enumerate(day.afternoon_activities):
            if str(act.id) == str(activity_id):
                logger.info(f"Found activity {activity_id} in afternoon activities")
                activity_found = True
                affected_day = day
                day.afternoon_activities.pop(i)
                break
        
        if activity_found:
            break
    
    if not activity_found:
        raise HTTPException(status_code=404, detail=f"Activity with ID {activity_id} not found in itinerary")
    
    # Recalculate routes for the affected day
    if affected_day:
        all_places = [act.place for act in affected_day.morning_activities + affected_day.afternoon_activities]
        if len(all_places) > 1:  # Only recalculate if there are at least 2 places
            polylines_duration_list = get_polylines_on_places(all_places)
            affected_day.routes = polylines_duration_list
        else:
            affected_day.routes = []  # No routes needed if 0 or 1 place
    
    # Update the cached trip response
    trip_response.itinerary = itinerary
    
    # Ensure all required fields are set before saving
    if not hasattr(trip_response, 'trip_type') or not trip_response.trip_type:
        trip_response.trip_type = "place"  # Default to place if missing
        
    if not hasattr(trip_response, 'template_type') or not trip_response.template_type:
        trip_response.template_type = TemplateType.MODERATE
    
    
    if not hasattr(trip_response, 'id') or not trip_response.id:
        trip_response.id = trip_id
    
    # Convert to dict and save to cache
    trip_dict = trip_response.dict()
    redis_cache.set(f"trip:{trip_id}:response", json.dumps(trip_dict, cls=PydanticJSONEncoder), ttl=604800)

    return {
        "response": {
            "itinerary": itinerary
        }
    }

