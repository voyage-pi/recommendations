from random import betavariate
import typing
from app.attributes import budget_dic
from app.schemas.Activities import PlaceInfo, PriceRange,LatLong
from typing import List,Dict,Set ,Tuple,Union
from pathlib import Path
from app.attributes.budget_dic import average_prices
from app.attributes.continents_bounds import continent_bounds 

import json

from app.schemas.Questionnaire import Place

BASE_DIR = Path(__file__).resolve().parent.parent  # Diretório do script atual
TYPES_PATH = BASE_DIR / "attributes" / "generic_types.json"


class CategoryMatcher:
    def __init__(self, json_path: Path):
        with json_path.open( 'r', encoding='utf-8') as f:
            self.category_map: Dict[str, List[str]] = json.load(f)
            self.category_sets: Dict[str, Set[str]] = {
                category: set(types) for category, types in self.category_map.items()
            }

    @staticmethod
    def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union) if union else 0.0

    def infer_category(self, place_types: List[str]) -> str:
        place_type_set = set(place_types)
        best_match = None
        best_score = -1.0

        for category, category_types in self.category_sets.items():
            score = self.jaccard_similarity(place_type_set, category_types)
            if score > best_score:
                best_score = score
                best_match = category

        return best_match

matcher=CategoryMatcher(TYPES_PATH)

def get_continent_from_coords(cood:LatLong) -> str:
    lat=cood.latitude
    lon=cood.longitude
    for continent, bounds in continent_bounds.items():
        if bounds["lat"][0] <= lat <= bounds["lat"][1] and bounds["lon"][0] <= lon <= bounds["lon"][1]:
            return continent
    return "Unknown"


def fit_places_on_price(prices:List[Tuple[PlaceInfo,PriceRange]],budget:int)->Tuple[List[PlaceInfo],PriceRange]:
    places_inside_budget=[]
    total_range=PriceRange(start_price=0.0,end_price=0.0,currency="")
    factor=0.15
    for (place,price) in prices:
        if total_range.end_price + price.end_price < budget+ budget*factor:
            total_range.start_price+=price.start_price
            total_range.end_price+=price.end_price
            total_range.currency=price.currency
            places_inside_budget.append(place)

    return places_inside_budget,total_range
    

def place_price(places:List[PlaceInfo])->List[Tuple[PlaceInfo,PriceRange]]:
    place_price:List[Tuple[PlaceInfo,PriceRange]]=[]
    for place in places:
        continent=get_continent_from_coords(place.location)
        currency=average_prices["cultural"][continent]["currency"]
        if place.price_range is not None:
            place_price.append((place,place.price_range)) 
            continue
        if place.price_level is not None:
            price_level=place.price_level 
            print(price_level)
            if price_level=="FREE":
                place_price.append((place,PriceRange(start_price=0.0,end_price=0.0,currency="$"))) 
            elif price_level=="INEXPENSIVE":
                place_price.append((place,PriceRange(start_price=1,end_price=15,currency="$"))) 
            elif price_level=="MODERATE":
                place_price.append((place,PriceRange(start_price=15,end_price=40,currency="$"))) 
            elif price_level=="EXPENSIVE":
                place_price.append((place,PriceRange(start_price=40,end_price=100,currency="$"))) 
            elif price_level=="VERY_EXPENSIVE":
                # here the end_price is just to limit the range since this is essentially +100$
                place_price.append((place,PriceRange(start_price=100,end_price=200,currency="$"))) 
            continue 
        best_match_generic_type=matcher.infer_category(place.types)
        free_types=('landmarks')
        # get the currency
        # Filter the free location attributes of places
        if best_match_generic_type in free_types:
            place_price.append((place,PriceRange(start_price=0,end_price=0,currency=currency)))
            continue
        if best_match_generic_type in average_prices.keys():
            if continent == "Unknown":
                place_price.append((place,PriceRange(start_price=0,end_price=0,currency=currency))) 
            factor=0.1
            value=average_prices[best_match_generic_type][continent]["price"]
            deviation=value*factor
            start_price=value-deviation 
            end_price=value+deviation 
            place_price.append((place,PriceRange(start_price=start_price,end_price=end_price,currency=currency)))
    print([f"{p.name} -> {v}\n" for (p,v) in place_price])
    # x is a (PlaceInfo,PriceRange) type, this is important for the SFJ (shortest job first), basically tries to couple the cheaper places before the rest
    sorted(place_price,key=lambda x: x[1].start_price)
    return place_price 
    #option 1 get the price range from google (verify) 
    #option 2 get the yelp prices by range
    #option 3 get the mapping from json 
