from typing import List, Dict, TypedDict
from app.schemas.Activities import TimeSlot


class TimeSlotActivityPair(TypedDict):
    """Represents a pairing of time slot with activity type"""
    time_slot: TimeSlot  # The time slot (morning or afternoon)
    activity_type: str   # The generic activity type category


def create_timeslot_activity_pair(time_slot: TimeSlot, activity_type: str) -> TimeSlotActivityPair:
    """Helper function to create a TimeSlotActivityPair"""
    return {"time_slot": time_slot, "activity_type": activity_type}


def extract_activity_pairs(distribution: Dict[TimeSlot, Dict[str, int]]) -> List[TimeSlotActivityPair]:
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