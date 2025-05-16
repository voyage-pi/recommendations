from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, TypedDict, Set
import random
from app.schemas.Activities import (
    ActivityType,
    TemplateType,
    TimeSlot,
    PlaceInfo,
    Activity,
    DayItinerary,
    TripItinerary,
    get_activity_duration,
)
from app.schemas.GenericTypes import GenericType, SPECIFIC_TO_GENERIC
from app.schemas.ItineraryTypes import (
    TimeSlotActivityPair,
    create_timeslot_activity_pair,
)
from app.handlers.ranking_handler import (
    rank_places,
    rank_by_rating,
    rank_by_price,
    rank_by_accessibility,
    rank_by_prominence,
    rank_by_landmark_status,
    compose_rankings,
    get_ranking_weights,
)
import logging



logger = logging.getLogger("uvicorn.error")

def get_activities_count(template_type: TemplateType) -> Dict[TimeSlot, int]:
    """Determine number of activities based on template type"""
    if template_type == TemplateType.LIGHT:
        return {TimeSlot.MORNING: 2, TimeSlot.AFTERNOON: 2}
    elif template_type == TemplateType.MODERATE:
        return {TimeSlot.MORNING: 3, TimeSlot.AFTERNOON: 4}
    else:
        return {TimeSlot.MORNING: 4, TimeSlot.AFTERNOON: 5}


def filter_places_by_type(
    places: List[PlaceInfo],
    included_types: List[ActivityType],
    excluded_types: List[ActivityType],
) -> List[PlaceInfo]:
    """Filter places based on included/excluded types"""
    filtered_places = []

    for place in places:
        place_type_matches = False
        for place_type in place.types:
            try:
                activity_type = ActivityType(place_type)
                if (
                    activity_type in included_types
                    and activity_type not in excluded_types
                ):
                    place_type_matches = True
                    break
            except ValueError:
                continue

        if place_type_matches:
            filtered_places.append(place)

    return filtered_places


def determine_activity_duration(place: PlaceInfo) -> int:
    """Determine the duration for a specific place based on its primary type"""
    for place_type in place.types:
        try:
            activity_type = ActivityType(place_type)
            return get_activity_duration(activity_type)
        except ValueError:
            continue

    return 60  # Default duration is 1 hour


def get_activity_type(place: PlaceInfo) -> ActivityType:
    """Determine the primary activity type for a place"""
    for place_type in place.types:
        try:
            return ActivityType(place_type)
        except ValueError:
            continue

    # Default to tourist_attraction or a common type that should be in all deployments
    return ActivityType("tourist_attraction")


def distribute_activities_for_day(
    generic_type_scores: Dict[str, float],
    total_activities: int,
) -> Dict[str, int]:
    generic_type_scores = generic_type_scores.copy()
    generic_type_scores.pop("transportation", None)
    generic_type_scores.pop("accommodation", None)
    generic_type_scores.pop("shopping", None)
    generic_type_scores.pop("food", None)
    generic_type_scores.pop("nightlife", None)

    logger.info(f"Total activities to distribute: {total_activities}")
    logger.info(f"Input generic type scores: {generic_type_scores}")

    assert total_activities > 0, "At least one activity is required"
    assert generic_type_scores, "Generic type scores are required"


    # Calculate landmark-related scores for distribution
    landmark_types = ["cultural", "historic"]
    has_landmarks = any(t in generic_type_scores for t in landmark_types)
    
    landmark_quota = 0
    if has_landmarks:
        landmark_score = sum(generic_type_scores.get(t, 0) for t in landmark_types)
        total_score = sum(generic_type_scores.values())
        
        if total_score > 0:
            landmark_ratio = landmark_score / total_score
            base_quota = max(1, int(total_activities * 0.3))
            score_adjusted_quota = int(total_activities * landmark_ratio)
            landmark_quota = min(base_quota, score_adjusted_quota)
            
            logger.info(f"Landmark ratio: {landmark_ratio}, Base quota: {base_quota}, Score adjusted: {score_adjusted_quota}")
            logger.info(f"Reserved {landmark_quota} slots for landmark activities")
    
    remaining_activities = total_activities - landmark_quota
    
    distribution_scores = generic_type_scores.copy()
    
    landmark_scores = {}
    for ltype in landmark_types:
        if ltype in distribution_scores:
            landmark_scores[ltype] = distribution_scores.pop(ltype)
    
    total_score = sum(distribution_scores.values())
    if total_score == 0:
        total_score = 1

    normalized_scores = {
        category: score / total_score for category, score in distribution_scores.items()
    }
    logger.info(f"Normalized scores: {normalized_scores}")

    distribution = {}
    for category, score in normalized_scores.items():
        desired_count = int(round(score * remaining_activities))
        distribution[category] = min(desired_count, generic_type_scores[category])

    if landmark_scores:
        total_landmark_score = sum(landmark_scores.values())
        if total_landmark_score > 0:
            for ltype, score in landmark_scores.items():
                ltype_quota = int(round((score / total_landmark_score) * landmark_quota))
                distribution[ltype] = ltype_quota
    
    logger.info(f"Initial distribution: {distribution}")

    current_total = sum(distribution.values())
    
    if current_total < total_activities:
        categories = sorted(
            distribution.keys(),
            key=lambda x: (x in landmark_types, normalized_scores.get(x, 0)),
            reverse=True,
        )
        
        for category in categories:
            if current_total >= total_activities:
                break
            distribution[category] += 1
            current_total += 1
    
    elif current_total > total_activities:
        categories = sorted(
            distribution.keys(),
            key=lambda x: (x not in landmark_types, normalized_scores.get(x, 0)),
        )
        
        for category in categories:
            if current_total <= total_activities:
                break
            if distribution[category] > 0:
                distribution[category] -= 1
                current_total -= 1

    logger.info(f"Final day distribution: {distribution}")
    return distribution


def assign_to_time_slots(
    day_activities: List[Activity],
    activities_count: Dict[TimeSlot, int],
    morning_start: int = 9,
    afternoon_start: int = 14,
) -> Dict[TimeSlot, List[Activity]]:
    """
    Assigns activities to morning and afternoon slots based on the count requirements.
    Returns a dictionary with time slots as keys and lists of activities as values.
    """
    # Sort activities by some criteria (could be type priority, duration, etc.)
    # For simplicity, we'll use the existing order
    morning_count = activities_count[TimeSlot.MORNING]
    afternoon_count = activities_count[TimeSlot.AFTERNOON]
    
    # Make a copy to avoid modifying the original list
    activities = day_activities.copy()
    
    # Assign activities to slots
    morning_activities = activities[:morning_count] if len(activities) >= morning_count else activities
    afternoon_activities = activities[morning_count:morning_count+afternoon_count] if len(activities) > morning_count else []
    
    # Now reschedule the activities based on their assigned time slots
    date = morning_activities[0].start_time.date() if morning_activities else afternoon_activities[0].start_time.date()
    
    # Reschedule morning activities
    current_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=morning_start)
    for activity in morning_activities:
        end_time = current_time + timedelta(minutes=activity.duration)
        activity.start_time = current_time
        activity.end_time = end_time
        current_time = end_time + timedelta(minutes=30)  # 30-minute gap between activities
    
    # Reschedule afternoon activities
    current_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=afternoon_start)
    for activity in afternoon_activities:
        end_time = current_time + timedelta(minutes=activity.duration)
        activity.start_time = current_time
        activity.end_time = end_time
        current_time = end_time + timedelta(minutes=30)  # 30-minute gap between activities
    
    return {
        TimeSlot.MORNING: morning_activities,
        TimeSlot.AFTERNOON: afternoon_activities
    }


def create_timeslot_activity_pair(
    time_slot: TimeSlot, activity_type: str
) -> TimeSlotActivityPair:
    """Helper function to create a TimeSlotActivityPair"""
    return {"time_slot": time_slot, "activity_type": activity_type}


def select_places_for_category(
    pre_ranked_places: List[PlaceInfo],
    count: int,
    used_place_ids: Set[str]
) -> List[PlaceInfo]:
    """
    Select places for a category from pre-ranked places
    while ensuring variety and focusing on important landmarks.
    """
    if not pre_ranked_places or count <= 0:
        return []

    # Filter out already used places
    available_places = [p for p in pre_ranked_places if p.id not in used_place_ids]
    if not available_places:
        return []
    
    # Ensure variety in selection by avoiding too many places of the same specific type
    selected_places = []
    types_seen = set()
    
    for place in available_places:
        if len(selected_places) >= count:
            break
            
        # Get the place's types
        place_types = set(place.types) if place.types else set()
        
        # If we've already seen all types but still have slots to fill, add anyway
        if not types_seen.intersection(place_types) or len(selected_places) < count - 1:
            selected_places.append(place)
            types_seen.update(place_types)
    
    # If we couldn't find enough varied places, just add the highest ranked ones
    if len(selected_places) < count:
        remaining = count - len(selected_places)
        remaining_places = [p for p in available_places if p not in selected_places][:remaining]
        selected_places.extend(remaining_places)
    
    return selected_places


def generate_itinerary(
    places: List[PlaceInfo],
    places_by_generic_type: Dict[str, List[PlaceInfo]],
    start_date: datetime,
    end_date: datetime,
    generic_type_scores: Dict[str, float],
    template_type: TemplateType = TemplateType.MODERATE,
    budget: float = None,
) -> TripItinerary:
    """Generate a complete trip itinerary with improved landmark selection"""

    assert generic_type_scores, "Generic type scores are required"

    # number of activities for each day
    activities_count = get_activities_count(template_type)
    total_activities_per_day = sum(activities_count.values())

    days = []
    current_date = start_date
    used_place_ids = set()
    activity_id = 0
    
    # Find keyword-matched places
    keyword_places = [place for place in places if getattr(place, 'keyword_match', False)]
    
    # First day should include at least one keyword place if available
    include_keyword_place = len(keyword_places) > 0
    
    while current_date <= end_date:
        day_itinerary = DayItinerary(date=current_date)

        # Get distribution of activities by type for the entire day
        day_distribution = distribute_activities_for_day(
            generic_type_scores, total_activities_per_day
        )

        # Select places for the entire day
        day_activities = []
        
        # If this is the first day and we have keyword places, make sure to include one
        if include_keyword_place and current_date.date() == start_date.date():
            # Find a keyword place that hasn't been used yet
            available_keyword_places = [p for p in keyword_places if p.id not in used_place_ids]
            
            if available_keyword_places:
                # Choose the keyword place with the highest rating
                selected_keyword_place = max(
                    available_keyword_places, 
                    key=lambda p: p.rating if p.rating is not None else 0
                )
                
                # Add this place first
                duration = determine_activity_duration(selected_keyword_place)
                activity_type = get_activity_type(selected_keyword_place)
                
                activity = Activity(
                    id=activity_id,
                    place=selected_keyword_place,
                    start_time=datetime.combine(current_date.date(), datetime.min.time()),
                    end_time=datetime.combine(current_date.date(), datetime.min.time()) + timedelta(minutes=duration),
                    activity_type=activity_type,
                    duration=duration,
                )
                
                day_activities.append(activity)
                used_place_ids.add(selected_keyword_place.id)
                activity_id += 1
                
                # We've included a keyword place, no need to do it again
                include_keyword_place = False
        
        for category, count in day_distribution.items():
            if category in places_by_generic_type and count > 0:
                # Use the improved place selection function
                selected_places = select_places_for_category(
                    places_by_generic_type[category], 
                    count, 
                    used_place_ids
                )

                # Schedule these places with a placeholder time for now
                if selected_places:
                    placeholder_time = datetime.combine(current_date.date(), datetime.min.time())
                    for place in selected_places:
                        duration = determine_activity_duration(place)
                        activity_type = get_activity_type(place)
                        
                        activity = Activity(
                            id=activity_id,
                            place=place,
                            start_time=placeholder_time,
                            end_time=placeholder_time + timedelta(minutes=duration),
                            activity_type=activity_type,
                            duration=duration,
                        )
                        
                        day_activities.append(activity)
                        used_place_ids.add(place.id)
                        activity_id += 1

        # Now assign these activities to time slots and reschedule them
        if day_activities:
            time_slot_activities = assign_to_time_slots(
                day_activities, activities_count
            )
            
            day_itinerary.morning_activities = time_slot_activities[TimeSlot.MORNING]
            day_itinerary.afternoon_activities = time_slot_activities[TimeSlot.AFTERNOON]
            
            days.append(day_itinerary)
        
        current_date += timedelta(days=1)

        # Break if we've used all places
        if len(used_place_ids) >= len(places):
            break

    return TripItinerary(
        start_date=start_date,
        end_date=(
            end_date if current_date > end_date else current_date - timedelta(days=1)
        ),
        days=days,
        name=""
    )


def format_itinerary_response(itinerary: TripItinerary) -> List[Dict]:
    """Format itinerary into a list of places with start/end times"""
    formatted_places = []

    for day in itinerary.days:
        for activity in day.morning_activities + day.afternoon_activities:
            formatted_places.append(
                {
                    "activity_id": activity.id,
                    "place_id": activity.place.id,
                    "name": activity.place.name,
                    "start_time": activity.start_time.isoformat(),
                    "end_time": activity.end_time.isoformat(),
                    "activity_type": activity.activity_type,
                    "duration": activity.duration,
                }
            )

    return formatted_places
