"""
TRIPPY Backend — Transport Tools

Estimates realistic transport options, legs, durations, and costs
between origin and destination with support for iterative cost refinement.
"""

from typing import List, Optional
from app.schemas.agent_outputs import TransportAgentOutput
from app.schemas.trip import TransportLeg, TransportMode, TravelStyle


CURRENCY_MULTIPLIERS = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 85.0,
    "JPY": 155.0,
}

INDIAN_CITIES = {
    "hyderabad", "delhi", "new delhi", "mumbai", "bombay", "bangalore", "bengaluru",
    "chennai", "madras", "kolkata", "calcutta", "jaipur", "goa", "kasol", "manali",
    "shimla", "agra", "varanasi", "kochi", "cochin", "pune", "ahmedabad", "udaipur",
    "rishikesh", "amritsar", "chandigarh", "lucknow", "mysore", "mysuru", "ooty",
    "darjeeling", "alleppey", "alappuzha", "hampi", "pondicherry", "puducherry",
    "leh", "ladakh", "srinagar", "gangtok", "guwahati", "shillong", "munnar",
    "kodaikanal", "jodhpur", "jaisalmer", "pushkar", "haridwar", "dehradun",
    "surat", "patna", "nagpur", "indore", "bhopal", "vadodara", "ludhiana",
    "kanpur", "thane", "pimpri-chinchwad", "ghaziabad", "nashik", "faridabad"
}

COUNTRY_KEYWORDS = {
    "india": "india",
    "bharat": "india",
    "japan": "japan",
    "italy": "italy",
    "france": "france",
    "spain": "spain",
    "indonesia": "indonesia",
    "switzerland": "switzerland",
    "germany": "germany",
    "uk": "uk",
    "united kingdom": "uk",
    "england": "uk",
    "usa": "usa",
    "united states": "usa",
    "thailand": "thailand",
    "singapore": "singapore",
    "uae": "uae",
    "dubai": "uae",
}

CITY_TO_COUNTRY = {
    "kyoto": "japan", "tokyo": "japan", "osaka": "japan", "nara": "japan", "hiroshima": "japan",
    "rome": "italy", "florence": "italy", "venice": "italy", "milan": "italy", "naples": "italy",
    "paris": "france", "nice": "france", "lyon": "france", "marseille": "france",
    "barcelona": "spain", "madrid": "spain", "seville": "spain", "valencia": "spain",
    "bali": "indonesia", "ubud": "indonesia", "jakarta": "indonesia", "seminyak": "indonesia",
    "interlaken": "switzerland", "zurich": "switzerland", "geneva": "switzerland",
    "london": "uk", "edinburgh": "uk", "manchester": "uk",
    "new york": "usa", "san francisco": "usa", "los angeles": "usa", "chicago": "usa",
    "bangkok": "thailand", "chiang mai": "thailand", "phuket": "thailand",
    "singapore": "singapore",
    "dubai": "uae", "abu dhabi": "uae",
}


def detect_country(location_str: str) -> str:
    """Robust country resolution for domestic and international origins/destinations."""
    loc = location_str.strip().lower()
    if not loc:
        return ""
    if "," in loc:
        parts = [p.strip() for p in loc.split(",")]
        last_part = parts[-1].lower()
        for kw, c in COUNTRY_KEYWORDS.items():
            if kw == last_part or kw in last_part:
                return c
        for kw, c in COUNTRY_KEYWORDS.items():
            for p in parts:
                if kw in p:
                    return c
    clean_city = loc.split(",")[0].strip().lower()
    if clean_city in INDIAN_CITIES or any(ic in loc for ic in INDIAN_CITIES):
        return "india"
    if clean_city in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[clean_city]
    for city, country in CITY_TO_COUNTRY.items():
        if city in loc:
            return country
    for kw, c in COUNTRY_KEYWORDS.items():
        if kw in loc:
            return c
    return ""


def estimate_transport(
    origin: str,
    destination: str,
    preferred_mode: TransportMode,
    travelers: int = 1,
    travel_style: TravelStyle = TravelStyle.cultural,
    refinement_level: int = 0,
    currency: str = "USD",
    live_forex_rate: Optional[float] = None,
    distance_km: Optional[float] = None,
    route_duration_hours: Optional[float] = None,
) -> TransportAgentOutput:
    """
    Estimates outbound and return transport between origin and destination.

    refinement_level:
      0: Standard realistic pricing based on user preference and travel style
      1: First budget reduction (Economy saver / off-peak transit)
      2: Aggressive budget reduction (Budget carrier / overland train / bus)
    """
    orig_country = detect_country(origin)
    dest_country = detect_country(destination)
    is_same_country = bool(orig_country and dest_country and orig_country == dest_country)
    is_same_region = is_same_country or any(
        c in origin.lower() and c in destination.lower()
        for c in ["italy", "japan", "spain", "france", "india", "usa", "germany", "uk", "indonesia"]
    )

    mode = preferred_mode
    if mode == TransportMode.mixed:
        mode = TransportMode.train if is_same_region else TransportMode.flight

    domestic_india = orig_country == dest_country == "india"
    rate = live_forex_rate if live_forex_rate is not None else CURRENCY_MULTIPLIERS.get(currency.upper(), 1.0)

    # Base cost estimation per person round-trip
    if is_same_region:
        if mode == TransportMode.train:
            base_pp = 95.0 if not domestic_india else 22.0
            duration_hours = route_duration_hours if route_duration_hours else (3.5 if "delhi" not in origin.lower() or "kasol" not in destination.lower() else 9.0)
        elif mode == TransportMode.bus:
            base_pp = 45.0 if not domestic_india else 15.0
            duration_hours = route_duration_hours if route_duration_hours else (6.0 if "delhi" not in origin.lower() or "kasol" not in destination.lower() else 10.5)
        elif mode == TransportMode.car:
            base_pp = 120.0 if not domestic_india else 40.0
            duration_hours = route_duration_hours if route_duration_hours else (4.0 if "delhi" not in origin.lower() or "kasol" not in destination.lower() else 9.5)
        else:
            base_pp = 140.0 if not domestic_india else 50.0
            duration_hours = route_duration_hours if route_duration_hours else 1.5
    else:
        # Long-distance / international
        if mode == TransportMode.flight:
            base_pp = 550.0
            duration_hours = 9.0
        elif mode == TransportMode.train:
            base_pp = 220.0
            duration_hours = 8.5
        else:
            base_pp = 380.0
            duration_hours = 12.0

    base_pp *= rate

    # Adjust for travel style
    if travel_style == TravelStyle.luxury:
        base_pp *= 1.7
    elif travel_style == TravelStyle.budget:
        base_pp *= 0.75

    # Apply refinement reductions
    if refinement_level == 1:
        # ~20% savings via economy saver / alternate timing
        base_pp *= 0.80
        tier_label = "Economy Saver"
    elif refinement_level >= 2:
        # ~35% savings via low-cost carrier or connecting route
        base_pp *= 0.65
        tier_label = "Deep-Discount Route"
    else:
        tier_label = "Standard Flexible"

    round_trip_cost = round(base_pp * travelers, 2)
    one_way_cost = round(round_trip_cost / 2.0, 2)

    legs: List[TransportLeg] = [
        TransportLeg(
            mode=mode,
            origin=origin,
            destination=destination,
            departure="Morning (08:30)",
            arrival=f"Day 1 (~{duration_hours:.1f}h transit)",
            cost_estimate=one_way_cost,
            notes=f"Outbound transfer ({tier_label}) for {travelers} traveler(s)",
        ),
        TransportLeg(
            mode=mode,
            origin=destination,
            destination=origin,
            departure="Afternoon (15:00)",
            arrival=f"Final Day (~{duration_hours:.1f}h transit)",
            cost_estimate=round(round_trip_cost - one_way_cost, 2),
            notes=f"Return transfer ({tier_label}) for {travelers} traveler(s)",
        ),
    ]

    alternatives = [
        f"Switch to off-peak train: save ~25% compared to peak timings",
        f"Non-refundable advance booking: save ~15%",
        f"Local public transit passes in {destination} for local exploration",
    ]

    return TransportAgentOutput(
        legs=legs,
        total_cost=round_trip_cost,
        total_duration_hours=round(duration_hours * 2.0, 1),
        primary_mode=mode,
        alternatives=alternatives,
    )
