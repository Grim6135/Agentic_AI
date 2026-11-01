"""
TRIPPY Backend — Stay & Activity Tools

Recommends accommodation categories, curated daily activities, and food budgets
matching destination, travel style, refinement levels, and selected currency.
"""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from app.schemas.agent_outputs import StayActivityAgentOutput
from app.schemas.trip import Accommodation, Activity, TravelStyle


DESTINATION_ACTIVITIES: Dict[str, List[Tuple[str, float, float, str]]] = {
    "kyoto": [
        ("Fushimi Inari Torii Gates Morning Walk", 3.0, 0.0, "Hike through thousands of vermilion torii gates at sunrise."),
        ("Kinkaku-ji (Golden Pavilion) Visit", 2.0, 15.0, "Iconic Zen Buddhist temple covered in gold leaf overlooking mirror pond."),
        ("Traditional Tea Ceremony in Gion", 2.0, 45.0, "Authentic matcha preparation and history with a tea master."),
        ("Arashiyama Bamboo Grove & Monkey Park", 3.5, 20.0, "Walk towering bamboo groves and visit Iwatayama scenic overlook."),
        ("Nishiki Market Culinary Tour", 2.5, 35.0, "Sample Kyoto specialties including skewers, dashi tamago, and matcha sweets."),
        ("Zen Meditation at Nanzen-ji Temple", 2.0, 15.0, "Experience quiet contemplation in an ancient rock garden temple."),
    ],
    "rome": [
        ("Colosseum & Roman Forum Guided Access", 3.5, 55.0, "Walk through gladiatorial history and imperial ruins."),
        ("Vatican Museums & Sistine Chapel", 4.0, 45.0, "Michelangelo frescoes, St. Peter's Basilica, and papal collections."),
        ("Trastevere Twilight Food & Wine Walk", 3.0, 60.0, "Taste authentic cacio e pepe, supplì, and local Lazio wines."),
        ("Trevi Fountain & Pantheon Historic Walk", 2.5, 0.0, "Self-guided evening walk through Rome's iconic piazzas."),
        ("Borghese Gallery & Villa Gardens", 2.5, 25.0, "Bernini sculptures and Caravaggio masterpieces."),
        ("Appian Way Bike Tour & Catacombs", 3.5, 35.0, "Cycle ancient Roman cobbles through historic aqueduct parks."),
    ],
    "bali": [
        ("Ubud Rice Terraces & Swing Experience", 3.0, 25.0, "Lush green agricultural terraces and scenic photo viewpoints."),
        ("Mount Batur Sunrise Volcano Trek", 5.0, 45.0, "Early morning trek with breakfast cooked over volcanic steam."),
        ("Uluwatu Cliff Temple & Kecak Fire Dance", 3.5, 20.0, "Dramatic coastal cliffs and traditional Balinese performance."),
        ("Balinese Cooking Class & Organic Farm", 4.0, 35.0, "Learn spicy sambal, satay, and herbal culinary secrets."),
        ("Nusa Penida Coastal Snorkel & Manta Tour", 6.0, 65.0, "Swim with manta rays and explore Kelingking Beach cliffs."),
        ("Traditional Spa & Herbal Massage Ritual", 2.0, 30.0, "Restorative Balinese massage with floral bath."),
    ],
    "paris": [
        ("Louvre Museum & Historic Masterpieces", 3.5, 30.0, "Explore the Mona Lisa, Winged Victory, and iconic palace galleries."),
        ("Eiffel Tower Summit & Trocadero Vista", 2.5, 35.0, "Ascend to the highest observation deck for panoramic vistas across Paris."),
        ("Seine River Sunset Architectural Cruise", 2.0, 22.0, "Glide past Notre-Dame Cathedral, Musée d'Orsay, and historic bridges."),
        ("Montmartre Bohemian Artists Quarter Walk", 3.0, 0.0, "Stroll historic cobblestones to Sacré-Cœur with sweeping city vistas."),
        ("Latin Quarter Pastry & Cafe Tasting Tour", 2.5, 40.0, "Taste artisanal macarons, warm croissants, and fine cheeses."),
        ("Musée d'Orsay Impressionist Highlights", 2.5, 20.0, "World-class collection of Monet, Degas, and Van Gogh inside a grand railway station."),
    ],
    "kasol": [
        ("Chalal Pine Forest Trail & Riverside Cafe Hop", 3.0, 5.0, "Walk the suspension footbridge across the Parvati River through pine woods to Chalal village."),
        ("Manikaran Sahib Gurudwara & Thermal Hot Springs", 3.5, 0.0, "Visit historic Gurudwara Manikaran Sahib, partake in communal langar, and see natural sulphur springs."),
        ("Tosh Village Himalayan Panorama Hike", 4.0, 10.0, "Ascend to high-altitude Tosh village for 360-degree vistas of snow-dusted Himalayan peaks."),
        ("Parvati Riverfront Nature Trail & Apple Orchards", 2.5, 0.0, "Peaceful self-guided walk along the rushing Parvati River flanked by pine valleys."),
        ("Kheerganga Alpine Meadow & Trailhead Trek", 5.0, 15.0, "Trek past cascading mountain waterfalls and cedar forests toward alpine pastures."),
        ("Himachali & Israeli Fusion Food Tasting Tour", 2.0, 12.0, "Savor authentic Himachali siddu and fresh river trout alongside warm shakshuka and pita."),
    ],
    "manali": [
        ("Solang Valley Adventure & Himalayan Vistas", 4.0, 20.0, "Spectacular valley vistas with paragliding, ropeway, and snow viewpoints."),
        ("Old Manali Bohemian Cafes & Cedar Wood Walk", 2.5, 0.0, "Wander quaint alleys, wooden Himachali homes, and artisanal cafes."),
        ("Jogini Waterfalls Nature Hike", 3.5, 5.0, "Serene trail passing through orchards leading to cascading mountain waterfalls."),
        ("Hadimba Temple Sacred Cedar Grove", 2.0, 5.0, "Ancient 16th-century wooden pagoda temple amidst towering deodars."),
    ],
    "goa": [
        ("Old Goa Portuguese Heritage & Basilicas Walk", 3.0, 10.0, "UNESCO heritage churches including Basilica of Bom Jesus and Se Cathedral."),
        ("Dudhsagar Waterfalls Jungle Safari Excursion", 5.0, 35.0, "Four-tiered waterfall adventure through lush Western Ghats forests."),
        ("Arabian Sea Sunset Catamaran Cruise", 2.5, 25.0, "Breezy coastal cruise watching for dolphins along the coastline."),
        ("Traditional Spice Plantation Walk with Goan Lunch", 3.5, 18.0, "Fragrant spice gardens, vanilla, cardamom, and authentic buffet."),
        ("Anjuna Coastal Cliff Trail & Beach Shacks", 2.5, 0.0, "Scenic red laterite coastal cliffs and lively seaside shacks."),
    ],
    "jaipur": [
        ("Amber Fort & Sheesh Mahal Heritage Tour", 3.5, 15.0, "Grand Rajput hilltop fortress with mirror palace and panoramic lake views."),
        ("Hawa Mahal & City Palace Royal Quarters", 3.0, 20.0, "Iconic Palace of Winds facade and museum of royal Rajasthani artifacts."),
        ("Nahargarh Fort Sunset Panorama", 2.5, 10.0, "Spectacular sunset views over the entire Pink City skyline."),
        ("Johari & Bapu Bazaar Artisan Walk", 2.5, 0.0, "Vibrant textile, gemstone, and handicraft lanes with traditional street treats."),
    ],
}

CURRENCY_MULTIPLIERS: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 85.0,
    "JPY": 155.0,
}


def _get_activities_for_destination(
    destination: str,
    landmarks: Optional[List[str]] = None,
) -> List[Tuple[str, float, float, str]]:
    """Finds matching curated activities or dynamically generates authentic ones using verified landmarks."""
    dest_lower = destination.lower()
    for key, acts in DESTINATION_ACTIVITIES.items():
        if key in dest_lower:
            return acts

    clean_name = destination.split(",")[0].strip()

    # If verified live landmarks are available from Wikipedia Geosearch, build authentic activities around them
    if landmarks:
        custom_acts = []
        for idx, lm in enumerate(landmarks[:8]):
            cost = 15.0 if idx % 2 == 1 else 0.0
            custom_acts.append((
                f"Explore {lm}",
                3.0,
                cost,
                f"Discover and explore verified landmark '{lm}' in {clean_name} [Source: Verified Geosearch POI].",
            ))
        if custom_acts:
            return custom_acts

    return [
        (f"{clean_name} Heritage & Cultural Exploration", 3.0, 15.0, f"Explore iconic cultural landmarks, historic quarters, and architecture across {clean_name}."),
        (f"{clean_name} Scenic Nature Trail & Panoramic Viewpoint", 3.5, 0.0, f"Scenic walk along picturesque local trails with panoramic viewpoints over {clean_name}."),
        (f"{clean_name} Traditional Cuisine & Street Food Tour", 2.5, 20.0, f"Taste authentic regional delicacies and culinary specialties in {clean_name}."),
        (f"{clean_name} Artisan Bazaar & Historic Market Walk", 2.5, 0.0, f"Stroll through vibrant local markets, handicraft stalls, and historic avenues in {clean_name}."),
        (f"{clean_name} Sunset Relaxation & Scenic Overlook", 2.0, 10.0, f"Unwind at a scenic sunset overlook and peaceful nature trail in {clean_name}."),
        (f"{clean_name} Town Center & Community Highlights Walk", 2.0, 0.0, f"Visit local heritage hubs, tranquil parks, and community landmarks across {clean_name}."),
    ]


def recommend_stays_and_activities(
    destination: str,
    travel_style: TravelStyle,
    start_date: date,
    duration_days: int,
    travelers: int = 1,
    interests: Optional[List[str]] = None,
    refinement_level: int = 0,
    currency: str = "USD",
    live_forex_rate: Optional[float] = None,
    landmarks: Optional[List[str]] = None,
) -> StayActivityAgentOutput:
    """
    Produces accommodation recommendations, activity schedules, and food estimates
    customized to the actual destination, currency, and travel style.
    """
    clean_city = destination.split(",")[0].strip()
    rate = live_forex_rate if live_forex_rate is not None else CURRENCY_MULTIPLIERS.get(currency.upper(), 1.0)
    is_inr = currency.upper() == "INR"

    # Base pricing per night based on style and refinement (in base USD units, then scaled)
    if refinement_level == 0:
        if travel_style == TravelStyle.luxury:
            tier = "luxury"
            hotel_name = f"Grand Palace Resort & Spa ({clean_city})"
            nightly_rate_base = 320.0 if not is_inr else 120.0
            daily_food_base = 95.0 if not is_inr else 35.0
        elif travel_style == TravelStyle.budget:
            tier = "budget"
            hotel_name = f"Central Traveler Guesthouse ({clean_city})"
            nightly_rate_base = 60.0 if not is_inr else 22.0
            daily_food_base = 30.0 if not is_inr else 10.0
        elif travel_style in [TravelStyle.romantic, TravelStyle.relaxation]:
            tier = "boutique"
            hotel_name = f"Boutique Heritage Inn & Suites ({clean_city})"
            nightly_rate_base = 180.0 if not is_inr else 65.0
            daily_food_base = 65.0 if not is_inr else 22.0
        else:
            tier = "midscale"
            hotel_name = f"City Center Boutique Hotel ({clean_city})"
            nightly_rate_base = 135.0 if not is_inr else 45.0
            daily_food_base = 50.0 if not is_inr else 18.0

    elif refinement_level == 1:
        tier = "midscale"
        hotel_name = f"Standard Comfort Inn & Suites ({clean_city})"
        nightly_rate_base = 95.0 if not is_inr else 32.0
        daily_food_base = 40.0 if not is_inr else 14.0

    else:
        tier = "budget"
        hotel_name = f"Eco Traveler Lodge & BnB ({clean_city})"
        nightly_rate_base = 55.0 if not is_inr else 18.0
        daily_food_base = 25.0 if not is_inr else 8.0

    # Scale by currency exchange rate
    nightly_rate = round(nightly_rate_base * rate, 2)
    daily_food = round(daily_food_base * rate, 2)

    # Accommodations need (duration_days - 1) nights, minimum 1
    nights = max(1, duration_days - 1)
    total_stay_cost = round(nightly_rate * nights, 2)
    total_food_cost = round(daily_food * duration_days * travelers, 2)

    # Curate activities specific to this destination
    activity_pool = _get_activities_for_destination(destination)
    selected_activities: List[Activity] = []

    # Map activities across days
    for day_idx in range(duration_days):
        act_template = activity_pool[day_idx % len(activity_pool)]
        act_date = start_date + timedelta(days=day_idx)
        act_name, duration_hours, cost_pp_base, desc = act_template

        # Scale activity cost by currency
        cost_pp = round(cost_pp_base * rate, 2)

        # In budget refinement level 2, cap activity fee or pick free alternative
        if refinement_level >= 2 and cost_pp > (20.0 * rate):
            cost_pp = 0.0
            act_name = f"Self-Guided Scenic Exploration ({act_name.split()[0]})"
            desc = f"Self-guided walk and free scenic landmark exploration in {clean_city}."

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

    currency_symbol = "₹" if is_inr else ("€" if currency.upper() == "EUR" else ("£" if currency.upper() == "GBP" else "$"))
    food_highlights = [
        f"Authentic local regional breakfast included at {hotel_name}",
        f"Casual dining recommendations (~{currency_symbol}{daily_food:.0f}/day per traveler)",
        f"Must-try culinary specialties of {clean_city}",
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
