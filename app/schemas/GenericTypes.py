from enum import Enum
from typing import Dict, List
import json
from pathlib import Path

class GenericType(str, Enum):
    CULTURAL = "cultural"
    OUTDOOR = "outdoor"
    SHOPPING = "shopping"
    FOOD = "food"
    ENTERTAINMENT = "entertainment"
    TRANSPORTATION = "transportation"
    ACCOMMODATION = "accommodation"
    WELLNESS = "wellness"
    SPORTS = "sports"
    NIGHTLIFE = "nightlife"
    LANDMARKS = "landmarks"

# Load generic type mappings from JSON
BASE_DIR = Path(__file__).resolve().parent.parent
GENERIC_TYPES_PATH = BASE_DIR / "attributes" / "generic_types.json"

with open(GENERIC_TYPES_PATH) as file:
    GENERIC_TYPE_MAPPING: Dict[str, List[str]] = json.load(file)

# Create reverse mapping (specific type -> generic type)
SPECIFIC_TO_GENERIC: Dict[str, str] = {}
for generic_type, specific_types in GENERIC_TYPE_MAPPING.items():
    for specific_type in specific_types:
        SPECIFIC_TO_GENERIC[specific_type] = generic_type

def get_generic_types(specific_types: List[str]) -> List[GenericType]:
    """
    Convert a list of specific place types into their corresponding generic types.
    Returns a list of unique generic types.
    """
    generic_types = set()
    for specific_type in specific_types:
        if specific_type in SPECIFIC_TO_GENERIC:
            generic_types.add(SPECIFIC_TO_GENERIC[specific_type])
    return list(generic_types) 