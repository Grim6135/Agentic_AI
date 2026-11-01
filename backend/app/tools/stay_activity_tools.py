"""
TRIPPY Backend — Stay & Activity Tools

Recommends accommodation categories, curated daily activities, and food budgets
matching destination, travel style, and refinement levels.
"""

from datetime import date, timedelta
from typing import List, Optional
from app.schemas.agent_outputs import StayActivityAgentOutput
from app.schemas.trip import Accommodation, Activity, TravelStyle


DESTINATION_ACTIVITIES = {
    "Kyoto": [
        ("Fushimi Inari Torii Gates Morning Walk", 3.0, 0.0, "Hike through thousands of vermilion torii gates at sunrise."),
        ("Kinkaku-ji (Golden Pavilion) Visit", 2.0, 15.0, "Iconic Zen Buddhist temple covered in gold leaf overlooking mirror pond."),
        ("Traditional Tea Ceremony in Gion", 2.0, 45.0, "Authentic matcha preparation and history with a tea master."),
        ("Arashiyama Bamboo Grove & Monkey Park", 3.5, 20.0, "Walk towering bamboo groves and visit Iwatayama scenic overlook."),
        ("Nishiki Market Culinary Tour", 2.5, 35.0, "Sample Kyoto specialties including skewers, dashi tamago, and matcha sweets."),
        ("Zen Meditation at Nanzen-ji Temple", 2.0, 15.0, "Experience quiet contemplation in an ancient rock garden temple."),
    ],
    "Rome": [
        ("Colosseum & Roman Forum Guided Access", 3.5, 55.0, "Walk through gladiatorial history and imperial ruins."),
        ("Vatican Museums & Sistine Chapel", 4.0, 45.0, "Michelangelo frescoes, St. Peter's Basilica, and papal collections."),
        ("Trastevere Twilight Food & Wine Walk", 3.0, 60.0, "Taste authentic cacio e pepe, supplì, and local Lazio wines."),
        ("Trevi Fountain & Pantheon Historic Walk", 2.5, 0.0, "Self-guided evening walk through Rome's iconic piazzas."),
        ("Borghese Gallery & Villa Gardens", 2.5, 25.0, "Bernini sculptures and Caravaggio masterpieces."),
        ("Appian Way Bike Tour & Catacombs", 3.5, 35.0, "Cycle ancient Roman cobbles through historic aqueduct parks."),
    ],
    "Bali": [
        ("Ubud Rice Terraces & Swing Experience", 3.0, 25.0, "Lush green agricultural terraces and scenic photo viewpoints."),
        ("Mount Batur Sunrise Volcano Trek", 5.0, 45.0, "Early morning trek with breakfast cooked over volcanic steam."),
        ("Uluwatu Cliff Temple & Kecak Fire Dance", 3.5, 20.0, "Dramatic coastal cliffs and traditional Balinese performance."),
        ("Balinese Cooking Class & Organic Farm", 4.0, 35.0, "Learn spicy sambal, satay, and herbal culinary secrets."),
        ("Nusa Penida Coastal Snorkel & Manta Tour", 6.0, 65.0, "Swim with manta rays and explore Kelingking Beach cliffs."),
        ("Traditional Spa & Herbal Massage Ritual", 2.0, 30.0, "Restorative Balinese massage with floral bath."),
    ],
}


def recommend_stays_and_activities(
    destination: str,
    travel_style: TravelStyle,
    start_date: date,
    duration_days: int,
    travelers: int = 1,
    interests: Optional[List[str]] = None,
    refinement_level: int = 0,
) -> StayActivityAgentOutput:
    """
    Produces accommodation recommendations, activity schedules, and food estimates.

    refinement_level:
      0: Standard selection aligned with travel style
      1: First budget optimization (tier down accommodation, swap highest-cost activity)
      2: Maximum budget optimization (guesthouse/hostel, prioritize free activities & street dining)
    """
    dest_key = next((k for k in DESTINATION_ACTIVITIES if k.lower() in destination.lower()), "Rome")

    # Base pricing per night based on style and refinement
    if refinement_level == 0:
        if travel_style == TravelStyle.luxury:
            tier = "luxury"
            hotel_name = f"Grand Palace Resort & Spa ({destination})"
            nightly_rate = 320.0
            daily_food = 95.0
        elif travel_style == TravelStyle.budget:
            tier = "budget"
            hotel_name = f"Central Traveler Guesthouse ({destination})"
            nightly_rate = 60.0
            daily_food = 30.0
        elif travel_style in [TravelStyle.romantic, TravelStyle.relaxation]:
            tier = "boutique"
            hotel_name = f"Boutique Heritage Inn & Suites ({destination})"
            nightly_rate = 180.0
            daily_food = 65.0
        else:
            tier = "midscale"
            hotel_name = f"City Center Boutique Hotel ({destination})"
            nightly_rate = 135.0
            daily_food = 50.0

    elif refinement_level == 1:
        # Step down accommodation tier
        tier = "midscale"
        hotel_name = f"Standard Comfort Inn & Suites ({destination})"
        nightly_rate = 95.0
        daily_food = 40.0

    else:
        # Step down to budget tier
        tier = "budget"
        hotel_name = f"Eco Traveler Lodge & BnB ({destination})"
        nightly_rate = 55.0
        daily_food = 25.0

    # Accommodations need (duration_days - 1) nights, minimum 1
    nights = max(1, duration_days - 1)
    total_stay_cost = round(nightly_rate * nights, 2)
    total_food_cost = round(daily_food * duration_days * travelers, 2)

    # Curate activities
    activity_pool = DESTINATION_ACTIVITIES[dest_key]
    selected_activities: List[Activity] = []

    # Map activities across days
    for day_idx in range(duration_days):
        act_template = activity_pool[day_idx % len(activity_pool)]
        act_date = start_date + timedelta(days=day_idx)

        act_name, duration_hours, cost_pp, desc = act_template

        # In budget refinement level 2, cap activity fee or pick free alternative
        if refinement_level >= 2 and cost_pp > 20.0:
            cost_pp = 0.0
            act_name = f"Self-Guided Scenic Exploration ({act_name.split()[0]})"
            desc = "Self-guided walk and free scenic landmark exploration."

        total_act_cost = round(cost_pp * travelers, 2)
        selected_activities.append(
            Activity(
                name=act_name,
                location=destination,
                date=act_date,
                duration_hours=duration_hours,
                cost_estimate=total_act_cost,
                description=desc,
            )
        )

    total_activities_cost = round(sum(a.cost_estimate or 0.0 for a in selected_activities), 2)

    food_highlights = [
        f"Authentic local regional breakfast included at {hotel_name}",
        f"Casual dining recommendations (~${daily_food:.0f}/day per traveler)",
        f"Must-try culinary specialties of {destination}",
    ]

    return StayActivityAgentOutput(
        accommodation_name=hotel_name,
        accommodation_category=tier,
        cost_per_night=nightly_rate,
        total_accommodation_cost=total_stay_cost,
        activities=selected_activities,
        total_activities_cost=total_activities_cost,
        daily_food_cost=daily_food,
        total_food_cost=total_food_cost,
        food_highlights=food_highlights,
    )
