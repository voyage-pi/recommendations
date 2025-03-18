from datetime import datetime, timedelta
from typing import List, Dict, Tuple
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


def generate_itinerary(
    places: List[PlaceInfo],
    included_types: List[ActivityType],
    excluded_types: List[ActivityType],
    start_date: datetime,
    end_date: datetime,
    template_type: TemplateType = TemplateType.MODERATE,
) -> TripItinerary:
    """Generate a complete trip itinerary"""
    filtered_places = filter_places_by_type(places, included_types, excluded_types)
    activities_count = get_activities_count(template_type)

    days = []
    current_date = start_date
    place_index = 0

    while current_date <= end_date:
        day_itinerary = DayItinerary(date=current_date)

        # Morning activities
        morning_count = activities_count[TimeSlot.MORNING]
        remaining_places = filtered_places[place_index:]
        morning_activities = schedule_activities(
            current_date, TimeSlot.MORNING, remaining_places, morning_count
        )
        day_itinerary.morning_activities = morning_activities
        place_index += len(morning_activities)

        # Afternoon activities
        afternoon_count = activities_count[TimeSlot.AFTERNOON]
        remaining_places = filtered_places[place_index:]
        afternoon_activities = schedule_activities(
            current_date, TimeSlot.AFTERNOON, remaining_places, afternoon_count
        )
        day_itinerary.afternoon_activities = afternoon_activities
        place_index += len(afternoon_activities)

        days.append(day_itinerary)
        current_date += timedelta(days=1)

        if place_index >= len(filtered_places):
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
                    "place_id": activity.place.place_id,
                    "name": activity.place.name,
                    "start_time": activity.start_time.isoformat(),
                    "end_time": activity.end_time.isoformat(),
                    "activity_type": activity.activity_type,
                    "duration": activity.duration,
                }
            )

    return formatted_places
