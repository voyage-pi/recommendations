from app.schemas.Activities import TripItinerary
from typing import List,Tuple
from abc import ABC, abstractmethod

class Metric(ABC):
    itinerary:TripItinerary

    def calculate(self,itinerary:TripItinerary)->float:
        pass


class Score:
    def __init__(self,metrics:List[Tuple[float,Metric]]) -> None:
        self.scores:List[Tuple[float,Metric]]=[]
    def add_metric(self,weight:float,metric:Metric):
        self.scores.append((weight,metric))
    def calculate_full_score(self,itinerary:TripItinerary)->float:
        return sum([w*m.calculate(itinerary)for (w,m) in self.scores])



