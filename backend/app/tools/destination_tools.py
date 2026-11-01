"""
TRIPPY Backend — Destination Tools

Reusable tools for destination knowledge lookup, ranking, and matchmaking
based on traveler style, interests, duration, and budget.
"""

from typing import Any, Dict, List, Optional
from app.schemas.agent_outputs import DestinationCandidate
from app.schemas.trip import TravelStyle


DESTINATION_CATALOG: List[Dict[str, Any]] = [
    {
        "name": "Kyoto, Japan",
        "country": "Japan",
        "styles": [TravelStyle.cultural, TravelStyle.relaxation, TravelStyle.romantic],
        "interests": ["history", "temples", "food", "nature", "photography", "architecture"],
        "cost_tier": "midscale",  # budget, midscale, luxury
        "avg_daily_cost": 160.0,
        "recommended_days": 5,
        "highlights": ["Fushimi Inari Shrine", "Arashiyama Bamboo Grove", "Gion District", "Kinkaku-ji"],
    },
    {
        "name": "Rome, Italy",
        "country": "Italy",
        "styles": [TravelStyle.cultural, TravelStyle.romantic, TravelStyle.family],
        "interests": ["history", "food", "art", "architecture", "photography"],
        "cost_tier": "midscale",
        "avg_daily_cost": 175.0,
        "recommended_days": 4,
        "highlights": ["Colosseum & Roman Forum", "Vatican Museums", "Trevi Fountain", "Trastevere Food Walk"],
    },
    {
        "name": "Bali, Indonesia",
        "country": "Indonesia",
        "styles": [TravelStyle.relaxation, TravelStyle.adventure, TravelStyle.budget, TravelStyle.romantic],
        "interests": ["beaches", "wellness", "nature", "surfing", "culture", "food"],
        "cost_tier": "budget",
        "avg_daily_cost": 85.0,
        "recommended_days": 7,
        "highlights": ["Ubud Rice Terraces", "Uluwatu Temple Sunset", "Mount Batur Sunrise Trek", "Seminyak Beach"],
    },
    {
        "name": "Swiss Alps (Interlaken), Switzerland",
        "country": "Switzerland",
        "styles": [TravelStyle.adventure, TravelStyle.luxury, TravelStyle.romantic],
        "interests": ["hiking", "mountains", "nature", "photography", "adventure sports"],
        "cost_tier": "luxury",
        "avg_daily_cost": 290.0,
        "recommended_days": 5,
        "highlights": ["Jungfraujoch Top of Europe", "Lake Brienz Cruise", "Lauterbrunnen Valley", "Harder Kulm"],
    },
    {
        "name": "Barcelona, Spain",
        "country": "Spain",
        "styles": [TravelStyle.cultural, TravelStyle.budget, TravelStyle.family],
        "interests": ["architecture", "beaches", "food", "art", "nightlife"],
        "cost_tier": "midscale",
        "avg_daily_cost": 150.0,
        "recommended_days": 5,
        "highlights": ["Sagrada Família", "Park Güell", "Gothic Quarter", "Barceloneta Beach"],
    },
    {
        "name": "Costa Rica (Arenal & Manuel Antonio)",
        "country": "Costa Rica",
        "styles": [TravelStyle.adventure, TravelStyle.family, TravelStyle.relaxation],
        "interests": ["wildlife", "rainforest", "nature", "beaches", "ziplining"],
        "cost_tier": "midscale",
        "avg_daily_cost": 140.0,
        "recommended_days": 6,
        "highlights": ["Arenal Volcano National Park", "Manuel Antonio Beaches", "Monteverde Cloud Forest", "Hot Springs"],
    },
    {
        "name": "Paris, France",
        "country": "France",
        "styles": [TravelStyle.romantic, TravelStyle.cultural, TravelStyle.luxury],
        "interests": ["art", "food", "fashion", "history", "architecture", "museums"],
        "cost_tier": "luxury",
        "avg_daily_cost": 240.0,
        "recommended_days": 5,
        "highlights": ["Eiffel Tower", "Louvre Museum", "Montmartre", "Seine River Cruise"],
    },
    {
        "name": "Bangkok & Chiang Mai, Thailand",
        "country": "Thailand",
        "styles": [TravelStyle.budget, TravelStyle.cultural, TravelStyle.adventure],
        "interests": ["street food", "temples", "night markets", "culture", "nature"],
        "cost_tier": "budget",
        "avg_daily_cost": 70.0,
        "recommended_days": 7,
        "highlights": ["Grand Palace Bangkok", "Chiang Mai Old City", "Elephant Sanctuary", "Chatuchak Market"],
    },
]


def rank_destination_candidates(
    origin: str,
    requested_destinations: Optional[List[str]],
    travel_style: TravelStyle,
    duration_days: int,
    budget_max: Optional[float],
    interests: List[str],
) -> List[DestinationCandidate]:
    """
    Ranks destination candidates using traveler style, interest overlap,
    budget viability, and trip duration.
    """
    candidates: List[DestinationCandidate] = []

    # If the user specified specific destinations, prioritize them
    if requested_destinations and len(requested_destinations) > 0:
        for idx, dest_name in enumerate(requested_destinations, start=1):
            matching_catalog = next(
                (d for d in DESTINATION_CATALOG if dest_name.lower() in d["name"].lower() or d["name"].lower() in dest_name.lower()),
                None,
            )
            country = matching_catalog["country"] if matching_catalog else "International"
            highlights = matching_catalog["highlights"] if matching_catalog else ["City center", "Local landmarks", "Historic sites"]
            score = 95.0 - (idx - 1) * 5.0

            candidates.append(
                DestinationCandidate(
                    name=dest_name,
                    country=country,
                    rank=idx,
                    match_score=score,
                    highlights=highlights,
                    recommended_days=duration_days,
                    why_matched=f"Explicitly requested by traveler from {origin}.",
                )
            )
        return candidates

    # Otherwise, score all catalog destinations
    scored = []
    user_interests_lower = {i.lower() for i in interests}

    for item in DESTINATION_CATALOG:
        score = 50.0  # baseline

        # Travel style match (+25 points)
        if travel_style in item["styles"]:
            score += 25.0

        # Interests overlap (up to +20 points)
        item_interests = {i.lower() for i in item["interests"]}
        overlap = len(user_interests_lower.intersection(item_interests))
        score += min(overlap * 6.0, 20.0)

        # Budget suitability (+5 points if budget matches cost tier)
        if budget_max is not None and duration_days > 0:
            est_total = item["avg_daily_cost"] * duration_days + 400.0  # rough baseline
            if est_total <= budget_max:
                score += 5.0
            else:
                score -= 10.0  # slight penalty for likely over-budget

        score = max(10.0, min(99.0, score))
        scored.append((score, item))

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)

    for rank, (score, item) in enumerate(scored[:4], start=1):
        candidates.append(
            DestinationCandidate(
                name=item["name"],
                country=item["country"],
                rank=rank,
                match_score=round(score, 1),
                highlights=item["highlights"],
                recommended_days=min(duration_days, item["recommended_days"]),
                why_matched=f"Strong fit for {travel_style.value} style with high alignment on {', '.join(item['interests'][:3])}.",
            )
        )

    return candidates
