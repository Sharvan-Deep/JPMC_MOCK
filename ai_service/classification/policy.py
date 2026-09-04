"""
CSR WASH Classification Policy & Domain Taxonomy for Task 6.
Defines positive community WASH pillars, negative industrial water exclusions,
evidence classification criteria, and confidence scoring rules.
"""

from typing import List, Set


class WASHPolicy:
    """Taxonomy and domain rules for classifying CSR WASH relevance."""

    # Pillar 1: Safe Drinking Water & Community Water Access
    DRINKING_WATER_TERMS: Set[str] = {
        "drinking water",
        "safe drinking water",
        "potable water",
        "water kiosk",
        "water atm",
        "ro plant",
        "reverse osmosis",
        "community water",
        "piped drinking water",
        "water purification",
        "water filtration",
        "borewell for drinking",
        "safe water access",
        "clean drinking water",
        "fluoride removal",
        "arsenic removal",
        "water supply to villages",
        "water tank for community",
    }

    # Pillar 2: Community Sanitation & Waste
    SANITATION_TERMS: Set[str] = {
        "sanitation",
        "toilet",
        "toilets",
        "community toilet",
        "school toilet",
        "sanitation block",
        "sanitation facility",
        "sanitation facilities",
        "open defecation",
        "open defecation free",
        "odf",
        "swachh bharat",
        "swachh vidyalaya",
        "public convenience",
        "urinal",
        "waste management in village",
        "solid and liquid waste management",
    }

    # Pillar 3: Hygiene & Behavioral Change
    HYGIENE_TERMS: Set[str] = {
        "hygiene",
        "hygiene awareness",
        "hygiene education",
        "handwashing",
        "hand washing",
        "menstrual hygiene",
        "menstrual hygiene management",
        "mhm",
        "sanitary napkin",
        "sanitary pad",
        "wash in schools",
        "wash awareness",
        "health and hygiene",
    }

    # Broad / Rural Watershed Terms (Partially Relevant when community-focused)
    WATERSHED_COMMUNITY_TERMS: Set[str] = {
        "watershed development",
        "rainwater harvesting in schools",
        "rainwater harvesting in community",
        "check dam",
        "village pond rejuvenation",
        "groundwater recharge for villages",
        "desilting of village tanks",
        "water conservation in villages",
    }

    # Negative Context: Industrial Operational Water (Non-WASH CSR)
    INDUSTRIAL_EXCLUSION_TERMS: Set[str] = {
        "effluent treatment plant",
        "etp",
        "zero liquid discharge",
        "zld",
        "cooling water",
        "process water",
        "cooling tower",
        "plant water consumption",
        "factory water",
        "water consumption per ton",
        "water consumption per mt",
        "industrial wastewater",
        "water recycling in plant",
        "water recycling in refinery",
        "manufacturing water",
        "smelter water",
        "power plant water",
    }

    @classmethod
    def get_system_prompt(cls) -> str:
        """Returns structured prompt for LLM providers."""
        return (
            "You are an expert CSR analyst evaluating corporate social responsibility filings for Jaldhaara Foundation.\n"
            "Your objective is to determine whether the company has engaged in genuine community WASH "
            "(Safe Drinking Water, Community Sanitation, Hygiene) CSR programs.\n\n"
            "STRICT RULES:\n"
            "1. Genuine WASH includes: safe drinking water kiosks, community RO plants, school/community toilets, "
            "open defecation prevention, menstrual hygiene, handwashing stations, community piped water.\n"
            "2. Distinguish context: Industrial water management (ETP, zero liquid discharge, cooling water, "
            "factory water efficiency) is NOT community WASH CSR and must be classified as NOT_WASH_RELEVANT.\n"
            "3. Generic rural watershed or check dam projects with incidental water impact should be PARTIALLY_RELEVANT.\n"
            "4. Return structured JSON with:\n"
            "   - classification: WASH_RELEVANT, PARTIALLY_RELEVANT, NOT_WASH_RELEVANT, or INSUFFICIENT_EVIDENCE\n"
            "   - confidence: float (0.0 to 1.0)\n"
            "   - water_relevance: boolean\n"
            "   - sanitation_relevance: boolean\n"
            "   - hygiene_relevance: boolean\n"
            "   - reasoning: explanation of the decision\n"
            "   - evidence: list of items with text, page, category, strength"
        )
