from typing import List, Tuple
from app.schemas.Questionnaire import Answer, QuestionType
from enum import Enum
import json


def questionnaire_to_attributes(answers: List[Answer]) -> Tuple[List[str], List[str]]:
    included_types: List[str] = []
    excluded_types: List[str] = []

    with open("../attributes/attributes_answer.json", "r") as file:
        data = json.load(file)
    for ans in answers:
        attrsIncluded, attrsExcluded = answers_attributes(ans, data)
        included_types.extend(attrsIncluded)
        excluded_types.extend(attrsExcluded)
    return included_types, excluded_types


# Reads the json with the attributes of each question of the forms
# Then makes the collection of the set of attributes depending on the question type
# Then applies the possible conditions
def answers_attributes(answer: Answer, data) -> Tuple[List[str], List[str]]:
    ansType: QuestionType = answer.type
    ansId: str = str(answer.question_id)
    ansValues = answer.value

    if ansType == "scale":
        return data[ansId], []
    elif ansType == "select":
        # selected is the union of attributes of the several selected cases
        # the ansValues is of type: [1,2,4] being the numbers the options selected
        options: dict = data[ansId]
        selected = [options[k] for i, k in enumerate(options) if i in ansValues]
        return selected, []
    else:
        return [], []
