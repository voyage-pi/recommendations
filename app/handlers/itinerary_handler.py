from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, TypedDict
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
    extract_activity_pairs,
)
from app.handlers.ranking_handler import (
    rank_places,
    rank_by_rating,
    rank_by_price,
    rank_by_accessibility,
    compose_rankings,
)


def get_activities_count(template_type: TemplateType) -> Dict[TimeSlot, int]:
    """Determine number of activities based on template type"""
    if template_type == TemplateType.LIGHT:
        return {TimeSlot.MORNING: 1, TimeSlot.AFTERNOON: 1}
    elif template_type == TemplateType.MODERATE:
        return {TimeSlot.MORNING: 2, TimeSlot.AFTERNOON: 2}
    else:
        return {TimeSlot.MORNING: 3, TimeSlot.AFTERNOON: 3}


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


def schedule_activities(
    date: datetime,
    time_slot: TimeSlot,
    places: List[PlaceInfo],
    count: int,
    morning_start: int = 9,
    afternoon_start: int = 14,
) -> List[Activity]:
    """Schedule activities for a specific time slot"""
    activities = []

    if time_slot == TimeSlot.MORNING:
        current_time = datetime.combine(date.date(), datetime.min.time()) + timedelta(
            hours=morning_start
        )
    else:  # AFTERNOON
        current_time = datetime.combine(date.date(), datetime.min.time()) + timedelta(
            hours=afternoon_start
        )

    selected_places = places[:count] if len(places) >= count else places

    for place in selected_places:
        duration = determine_activity_duration(place)
        activity_type = get_activity_type(place)

        # Create activity
        end_time = current_time + timedelta(minutes=duration)
        activity = Activity(
            place=place,
            start_time=current_time,
            end_time=end_time,
            activity_type=activity_type,
            duration=duration,
        )

        activities.append(activity)

        current_time = end_time + timedelta(minutes=30)

    return activities


def distribute_activities_by_scores(
    places: List[PlaceInfo],
    generic_type_scores: Dict[str, float],
    activities_count: Dict[TimeSlot, int],
) -> Dict[TimeSlot, Dict[str, int]]:
    """
    Distributes activities for each time slot based on category scores.
    Returns a dictionary with time slots as keys and category distributions as values.
    """
    # Calculate total number of activities for the day
    total_activities = sum(activities_count.values())

    assert total_activities > 0, "At least one activity is required"
    assert generic_type_scores, "Generic type scores are required"

    # Normalize scores
    total_score = sum(generic_type_scores.values())
    if total_score == 0:
        total_score = 1  # Avoid division by zero

    normalized_scores = {
        category: score / total_score for category, score in generic_type_scores.items()
    }

    # Count available places by generic type
    places_by_generic_type = {}
    for place in places:
        for place_type in place.types:
            if place_type in SPECIFIC_TO_GENERIC:
                generic_type = SPECIFIC_TO_GENERIC[place_type]
                if generic_type not in places_by_generic_type:
                    places_by_generic_type[generic_type] = 0
                places_by_generic_type[generic_type] += 1

    # Create initial distribution based on scores
    raw_distribution = {}
    for category, score in normalized_scores.items():
        # Calculate desired count, but don't allocate more than available places
        desired_count = int(round(score * total_activities))
        if category in places_by_generic_type:
            raw_distribution[category] = min(
                desired_count, places_by_generic_type[category]
            )
        else:
            raw_distribution[category] = 0

    # Adjust to match total_activities (might be slightly off due to rounding)
    current_total = sum(raw_distribution.values())

    # Distribute activities to each time slot
    result = {TimeSlot.MORNING: {}, TimeSlot.AFTERNOON: {}}

    # First, allocate morning activities
    morning_count = activities_count[TimeSlot.MORNING]
    remaining_distribution = raw_distribution.copy()

    # Prioritize categories with higher scores for morning
    sorted_categories = sorted(
        remaining_distribution.keys(),
        key=lambda x: normalized_scores.get(x, 0),
        reverse=True,
    )

    morning_allocated = 0
    for category in sorted_categories:
        if morning_allocated >= morning_count:
            break

        category_count = remaining_distribution[category]
        to_allocate = min(category_count, morning_count - morning_allocated)

        if to_allocate > 0:
            result[TimeSlot.MORNING][category] = to_allocate
            remaining_distribution[category] -= to_allocate
            morning_allocated += to_allocate

    # Then, allocate afternoon activities from what remains
    afternoon_count = activities_count[TimeSlot.AFTERNOON]
    afternoon_allocated = 0

    for category in sorted_categories:
        if afternoon_allocated >= afternoon_count:
            break

        category_count = remaining_distribution[category]
        to_allocate = min(category_count, afternoon_count - afternoon_allocated)

        if to_allocate > 0:
            result[TimeSlot.AFTERNOON][category] = to_allocate
            remaining_distribution[category] -= to_allocate
            afternoon_allocated += to_allocate

    return result


def create_timeslot_activity_pair(
    time_slot: TimeSlot, activity_type: str
) -> TimeSlotActivityPair:
    """Helper function to create a TimeSlotActivityPair"""
    return {"time_slot": time_slot, "activity_type": activity_type}


def extract_activity_pairs(
    distribution: Dict[TimeSlot, Dict[str, int]]
) -> List[TimeSlotActivityPair]:
    """
    Convert a time slot to category distribution into a list of TimeSlotActivityPair objects.
    Each pair represents a single activity to be scheduled.
    """
    pairs = []

    for time_slot, categories in distribution.items():
        for category, count in categories.items():
            # Create a pair for each individual activity (if count > 1)
            for _ in range(count):
                pairs.append(create_timeslot_activity_pair(time_slot, category))

    return pairs


def generate_itinerary(
    places: List[PlaceInfo],
    included_types: List[ActivityType],
    excluded_types: List[ActivityType],
    start_date: datetime,
    end_date: datetime,
    generic_type_scores: Dict[str, float],
    template_type: TemplateType = TemplateType.MODERATE,
) -> TripItinerary:
    """Generate a complete trip itinerary"""

    assert generic_type_scores, "Generic type scores are required"

    # number of activities for each day
    activities_count = get_activities_count(template_type)

    # Group places by generic type
    places_by_type = {}
    for place in places:
        for place_type in place.types:
            if place_type in SPECIFIC_TO_GENERIC:
                generic_type = SPECIFIC_TO_GENERIC[place_type]
                if generic_type not in places_by_type:
                    places_by_type[generic_type] = []
                places_by_type[generic_type].append(place)

    days = []
    current_date = start_date
    used_place_ids = set()

    # Create a composite ranking function that considers multiple factors
    ranking_function = compose_rankings([
        (rank_by_rating, 0.5),      # 50% weight to ratings
        (rank_by_price, 0.3),       # 30% weight to price
        (rank_by_accessibility, 0.2) # 20% weight to accessibility
    ])

    while current_date <= end_date:
        day_itinerary = DayItinerary(date=current_date)

        # {<TimeSlot.MORNING: 'morning'>: {'cultural': 2}
        distribution: Dict[TimeSlot, Dict[str, int]] = distribute_activities_by_scores(
            places, generic_type_scores, activities_count
        )

        morning_activities = []
        for category, count in distribution[TimeSlot.MORNING].items():
            if category in places_by_type and count > 0:
                # Filter out used places and rank the remaining ones
                available_places = [
                    p for p in places_by_type[category] if p.id not in used_place_ids
                ]
                ranked_places = rank_places(available_places, ranking_function)
                selected_places = ranked_places[:count]

                if selected_places:
                    activities = schedule_activities(
                        current_date,
                        TimeSlot.MORNING,
                        selected_places,
                        len(selected_places),
                    )
                    morning_activities.extend(activities)
                    for place in selected_places:
                        used_place_ids.add(place.id)

        day_itinerary.morning_activities = morning_activities

        # Afternoon activities
        afternoon_activities = []
        for category, count in distribution[TimeSlot.AFTERNOON].items():
            if category in places_by_type and count > 0:
                # Filter out used places and rank the remaining ones
                available_places = [
                    p for p in places_by_type[category] if p.id not in used_place_ids
                ]
                ranked_places = rank_places(available_places, ranking_function)
                selected_places = ranked_places[:count]

                if selected_places:
                    activities = schedule_activities(
                        current_date,
                        TimeSlot.AFTERNOON,
                        selected_places,
                        len(selected_places),
                    )
                    afternoon_activities.extend(activities)
                    for place in selected_places:
                        used_place_ids.add(place.id)

        day_itinerary.afternoon_activities = afternoon_activities
        days.append(day_itinerary)
        current_date += timedelta(days=1)

        # Break if we've used all places
        if len(used_place_ids) >= len(places):
            break

    return TripItinerary(
        id=random.randint(1000, 9999),  # Placeholder ID
        start_date=start_date,
        end_date=(
            end_date if current_date > end_date else current_date - timedelta(days=1)
        ),
        days=days,
    )


def format_itinerary_response(itinerary: TripItinerary) -> List[Dict]:
    """Format itinerary into a list of places with start/end times"""
    formatted_places = []

    for day in itinerary.days:
        for activity in day.morning_activities + day.afternoon_activities:
            formatted_places.append(
                {
                    "place_id": activity.place.id,
                    "name": activity.place.name,
                    "start_time": activity.start_time.isoformat(),
                    "end_time": activity.end_time.isoformat(),
                    "activity_type": activity.activity_type,
                    "duration": activity.duration,
                }
            )

    return formatted_places
