from typing import List, Dict, Callable, Tuple, Set
from app.schemas.Activities import PlaceInfo

def rank_by_rating(places: List[PlaceInfo]) -> List[PlaceInfo]:
    """Ranks places by their rating"""
    # Filter out places without ratings and sort by rating
    rated_places = [p for p in places if p.rating is not None]
    unrated_places = [p for p in places if p.rating is None]
    
    # Sort rated places by rating in descending order
    sorted_rated_places = sorted(rated_places, key=lambda x: x.rating, reverse=True)
    
    # Combine sorted rated places with unrated places
    return sorted_rated_places + unrated_places

def rank_by_price(places: List[PlaceInfo]) -> List[PlaceInfo]:
    """Ranks places by their price range"""
    # Define price range order (from cheapest to most expensive)
    price_order = {
        "FREE": 0,
        "INEXPENSIVE": 1,
        "MODERATE": 2,
        "EXPENSIVE": 3,
        "VERY_EXPENSIVE": 4
    }
    
    # Sort places by price range
    return sorted(
        places,
        key=lambda x: price_order.get(x.price_range, float('inf'))
    )

def rank_by_accessibility(places: List[PlaceInfo]) -> List[PlaceInfo]:
    """Ranks places by their accessibility options"""
    def get_accessibility_score(place: PlaceInfo) -> float:
        if not place.accessibility_options:
            return 0.0
        
        # Count the number of accessibility options
        options_count = len(place.accessibility_options)
        # Normalize by the maximum possible options (assuming we know all possible options)
        max_options = 10  # This should be adjusted based on your actual maximum
        return options_count / max_options
    
    return sorted(places, key=get_accessibility_score, reverse=True)

def rank_by_prominence(places: List[PlaceInfo]) -> List[PlaceInfo]:
    """
    Ranks places by their prominence/importance using user_ratings_total 
    as a proxy for popularity
    """
    # Some places might not have user_ratings_total, default to 0
    return sorted(
        places, 
        key=lambda x: getattr(x, 'user_ratings_total', 0) or 0, 
        reverse=True
    )

def rank_by_landmark_status(places: List[PlaceInfo]) -> List[PlaceInfo]:
    """
    Ranks places by whether they are major landmarks based on place types
    """
    landmark_types = {
        "tourist_attraction",
        "point_of_interest",
        "establishment",
        "landmark",
        "natural_feature",
        "museum",
        "historic",
        "monument",
        "church",
        "place_of_worship",
        "park"
    }
    
    def get_landmark_score(place: PlaceInfo) -> float:
        if not place.types:
            return 0.0
            
        # Count how many landmark type categories this place matches
        matching_types = set(place.types) & landmark_types
        return len(matching_types) / len(landmark_types)
    
    return sorted(places, key=get_landmark_score, reverse=True)

def get_ranking_weights(generic_type: str) -> List[Tuple[Callable, float]]:
    """
    Returns different ranking weights based on place category
    """
    if generic_type in ["cultural", "landmarks"]:
        return [
            (rank_by_landmark_status, 0.4),
            (rank_by_prominence, 0.3),
            (rank_by_rating, 0.2),
            (rank_by_accessibility, 0.1)
        ]
    elif generic_type in ["outdoor", "nature"]:
        return [
            (rank_by_rating, 0.4),
            (rank_by_accessibility, 0.3),
            (rank_by_prominence, 0.2),
            (rank_by_landmark_status, 0.1)
        ]
    elif generic_type in ["food", "restaurant"]:
        return [
            (rank_by_rating, 0.5),
            (rank_by_price, 0.3),
            (rank_by_prominence, 0.2)
        ]
    # Default weights for other categories
    return [
        (rank_by_rating, 0.3),
        (rank_by_prominence, 0.3),
        (rank_by_landmark_status, 0.2),
        (rank_by_price, 0.2)
    ]

def compose_rankings(
    rankings: List[Tuple[Callable[[List[PlaceInfo]], List[PlaceInfo]], float]]
) -> Callable[[List[PlaceInfo]], List[PlaceInfo]]:
    """
    Composes multiple ranking functions with their weights.
    Each ranking function should return a sorted list of places.
    Weights should sum to 1.0.
    
    Args:
        rankings: List of tuples containing (ranking_function, weight)
    
    Returns:
        A new ranking function that combines the input rankings
    """
    # Validate weights sum to 1.0
    total_weight = sum(weight for _, weight in rankings)
    if abs(total_weight - 1.0) > 0.0001:  # Allow for small floating point errors
        raise ValueError("Ranking weights must sum to 1.0")
    
    def combined_ranking(places: List[PlaceInfo]) -> List[PlaceInfo]:
        if not places:
            return []
            
        # Calculate scores for each place based on all rankings
        place_scores: Dict[str, float] = {}
        
        for place in places:
            total_score = 0.0
            for ranking_fn, weight in rankings:
                # Get the rank of the place in this ranking's ordering
                ranked_places = ranking_fn(places)
                rank = ranked_places.index(place)
                # Normalize rank to [0,1] and invert so higher rank = higher score
                normalized_score = 1.0 - (rank / len(places))
                total_score += normalized_score * weight
            
            place_scores[place.id] = total_score
        
        # Sort places by their total score
        return sorted(places, key=lambda x: place_scores[x.id], reverse=True)
    
    return combined_ranking

def rank_places(
    places: List[PlaceInfo],
    ranking_fn: Callable[[List[PlaceInfo]], List[PlaceInfo]]
) -> List[PlaceInfo]:
    """
    Rank a list of places using the specified ranking function
    """
    return ranking_fn(places) 

def pre_rank_places_by_category(
    places_by_generic_type: Dict[str, List[PlaceInfo]]
) -> Dict[str, List[PlaceInfo]]:
    """
    Pre-ranks all places by their generic type categories.
    Returns a dictionary mapping each category to its pre-ranked list of places.
    """
    pre_ranked_places = {}
    
    for category, places in places_by_generic_type.items():
        ranking_weights = get_ranking_weights(category)
        ranking_function = compose_rankings(ranking_weights)
        pre_ranked_places[category] = rank_places(places, ranking_function)
    
    return pre_ranked_places 