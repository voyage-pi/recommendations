from app.schemas.Questionnaire import Answer
from typing import List, Tuple


def transform_questionnaire(data: List[Answer]) -> Tuple[List[str], List[str]]:
    positive_tags = []
    negative_tags = []
    return positive_tags, negative_tags
