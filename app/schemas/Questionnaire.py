from typing import Any, int
from enum import Enum
from pydantic import BaseModel


class QuestionType(str, Enum):
    SCALE = "scale"


class Answer(BaseModel):
    question_id: int
    value: Any
    type: QuestionType
