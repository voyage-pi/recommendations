from app.schemas.Questionnaire import Answer
from typing import List, Tuple


def transform_questionnaire(data: List[Answer]) -> Tuple[List[str], List[str]]:
    included_types = []
    excluded_types = []
    return included_types, excluded_types
