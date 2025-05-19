from typing import List, Tuple, Dict
from app.schemas.Questionnaire import Answer, QuestionType
from app.schemas.GenericTypes import GenericType, SPECIFIC_TO_GENERIC
from enum import Enum
import json
from pathlib import Path
import requests as request 

BASE_DIR = Path(__file__).resolve().parent.parent  # Diretório do script atual
ATTRIBUTES_PATH = BASE_DIR / "attributes" / "attributes_answer.json"


def questionnaire_to_attributes(answers: List[Answer]) -> Tuple[List[str], List[str], Dict[str, float]]:
    included_types = ["tourist_attraction", "museum", "park", "restaurant", "cafe"]
    excluded_types = []
    generic_type_scores = {
        "cultural": 0.8,
        "landmarks": 0.8,
        "outdoor": 0.7,
        "entertainment": 0.6,
        "food": 0.6
    }
    return included_types, excluded_types, generic_type_scores

# Reads the json with the attributes of each question of the forms
# Then makes the collection of the set of attributes depending on the question type
# Then applies the possible conditions
def answers_attributes(answer: Answer, data) -> Tuple[List[str], List[str], Dict[str, float]]:
    ansType: QuestionType = answer.type
    ansId: str = str(answer.question_id)
    ansValues = answer.value
    generic_type_scores: Dict[str, float] = {}
    included_types: List[str] = []
    excluded_types: List[str] = []

    if ansType == "scale":
        # For scale questions, use the value directly as the score
        score = float(ansValues)
        generic_type = data[ansId]

        
        # Handle the case where generic_type is a dictionary (like for question 3)
        if isinstance(generic_type, dict):
            # Determine which key to use based on the score
            # For example, if score >= 3, use "ADVENTUROUS", else use "RELAXING"
            key = "ADVENTUROUS" if score >= 3 else "RELAXING"
            if key in generic_type:
                actual_generic_type = generic_type[key]
                if actual_generic_type:
                    generic_type_scores[actual_generic_type] = score
                    # Get all specific types for this generic type
                    included_types = [t for t, g in SPECIFIC_TO_GENERIC.items() if g == actual_generic_type]
        elif generic_type:  # Simple string case
            generic_type_scores[generic_type] = score
            # Get all specific types for this generic type
            included_types = [t for t, g in SPECIFIC_TO_GENERIC.items() if g == generic_type]
        return included_types, excluded_types, generic_type_scores
    
    elif ansType == "select":
        # For select questions, use 1.0 as the score for selected options
        options: dict = data[ansId]
        for i, k in enumerate(options):
            if i in ansValues:
                generic_type = options[k]
                if generic_type:
                    generic_type_scores[generic_type] = 1.0
                    # Get all specific types for this generic type
                    included_types.extend([t for t, g in SPECIFIC_TO_GENERIC.items() if g == generic_type])
        return included_types, excluded_types, generic_type_scores
    else:
        return [], [], {}
