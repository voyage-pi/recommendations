from typing import List, Tuple, Dict
from app.schemas.Questionnaire import Answer, QuestionType
from app.schemas.GenericTypes import GenericType, SPECIFIC_TO_GENERIC
from enum import Enum
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent  # Diretório do script atual
ATTRIBUTES_PATH = BASE_DIR / "attributes" / "attributes_answer.json"


def questionnaire_to_attributes(answers: List[Answer]) -> Tuple[List[str], List[str], Dict[str, float]]:
    included_types: List[str] = []
    excluded_types: List[str] = []
    generic_type_scores: Dict[str, float] = {}

    with open(ATTRIBUTES_PATH) as file:
        data = json.load(file)

    for ans in answers:
        attrsIncluded, attrsExcluded, scores = answers_attributes(ans, data)
        included_types.extend(attrsIncluded)
        excluded_types.extend(attrsExcluded)
        
        # Update generic type scores
        for generic_type, score in scores.items():
            if generic_type in generic_type_scores:
                generic_type_scores[generic_type] = max(generic_type_scores[generic_type], score)
            else:
                generic_type_scores[generic_type] = score

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
