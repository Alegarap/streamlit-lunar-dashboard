"""User profiles for Lunar Ventures team members.

Maps logged-in email → profile with role, domains, page visibility.
Base profiles are static; user-customizable preferences live in Supabase
(user_preferences table) and are merged at runtime by style.apply().
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# All pages (engineering sees all, GPs see a subset)
# ---------------------------------------------------------------------------

_ALL_PAGES = ["Home", "Discovery", "Clusters", "Ask AI", "Ingestion", "Cost Tracking", "My Profile", "For You (legacy)"]
_GP_PAGES = ["Home", "Discovery", "Clusters", "Ask AI", "Ingestion", "Cost Tracking", "My Profile"]

# ---------------------------------------------------------------------------
# Base profiles derived from scripts/reviewer_profiles.json
# Two roles for now: "Engineering" and "General Partner"
# ---------------------------------------------------------------------------

_PROFILES = {
    "alejandro": {
        "name": "Alejandro García",
        "linear_id": "db1376df-3efd-4b62-bc91-8f203ad9ef58",
        "role": "Engineering",
        "domains": ["all"],
        "description": "Engineering lead. Has access to all domains — never filter results for this user.",
        "visible_pages": _ALL_PAGES,
    },
    "morris": {
        "name": "Morris Clay",
        "linear_id": "9ba1f3c5-ee1e-43ed-bdf1-66d57b3147c3",
        "role": "General Partner",
        "domains": [
            "software", "data infrastructure", "edge AI", "compute hardware",
            "networking", "cooling", "new compute primitives", "health-tech",
            "AI infrastructure", "AI security",
        ],
        "description": "Software engineer & founder, 15+ years in ML/AI. Covers software/data, edge AI, compute hardware, networking, cooling, new compute primitives.",
        "visible_pages": _GP_PAGES,
    },
    "cindy": {
        "name": "Cindy Wei",
        "linear_id": "67e0f105-bd7d-4123-8152-79e043b4d1af",
        "role": "General Partner",
        "domains": [
            "life sciences", "genomics", "proteomics", "spatial biology",
            "organoids", "bioinformatics", "medical devices", "drug discovery",
            "cancer", "pharma", "clinical AI", "bioprocess", "metabolic",
            "pathology", "biomarker", "medical imaging",
        ],
        "description": "Bioinformatician and cancer biologist. Covers all bio/life sciences themes.",
        "visible_pages": _GP_PAGES,
    },
    "eyal": {
        "name": "Eyal Baroz",
        "linear_id": "6c67447c-159c-4b77-af40-b45faf46aba9",
        "role": "General Partner",
        "domains": [
            "robotic", "autonomous vehicle", "autonomous navigation", "drone",
            "teleoperation", "manipulation", "embodied AI", "defense hardware",
            "semiconductor", "chiplet", "chip design", "humanoid robot",
            "multi-robot", "spacecraft",
        ],
        "description": "25+ years in semiconductors, robotics, defense, telecom. Covers all robotics and autonomous systems.",
        "visible_pages": _GP_PAGES,
    },
    "mick": {
        "name": "Mick Halsband",
        "linear_id": "5f299ecd-e5a3-4ff8-92cf-bc30b847bc64",
        "role": "General Partner",
        "domains": [
            "climate", "resilience", "defense software", "geospatial",
            "satellite", "agriculture", "disaster management", "new materials",
        ],
        "description": "CTO background in mission-critical systems. Covers climate/resilience, defense (software side), satellite/geospatial.",
        "visible_pages": _GP_PAGES,
    },
    "alberto": {
        "name": "Alberto Cresto",
        "linear_id": "33249564-9934-485a-8f5a-3cae6d3a597e",
        "role": "General Partner",
        "domains": [
            "new materials", "nanomaterials", "advanced manufacturing",
            "battery", "energy storage", "solid-state electrolyte", "cathode", "anode",
            "hydrogen storage", "fuel cell",
            "semiconductor", "wide-bandgap", "quantum dot", "neuromorphic",
            "organic semiconductor", "spintronic", "piezoelectric", "ferroelectric",
            "combustion", "propulsion", "reacting flow", "hydrogen combustion",
            "construction materials", "concrete", "composite", "biodegradable",
            "metamaterial", "photonic", "acoustic metamaterial",
            "membrane", "desalination", "CO2 capture", "nanofiltration",
            "thermoelectric", "magnetocaloric", "energy conversion",
            "hydrogel", "spider silk", "peptide", "bio-inspired material",
            "superconductor", "nuclear material", "fusion",
            "aerogel", "catalysis", "computational chemistry",
        ],
        "description": "40+ deep tech investments. Covers materials science, energy storage, semiconductors, combustion ML, construction materials, metamaterials, membranes, and bio-inspired materials.",
        "visible_pages": _GP_PAGES,
    },
    "florent": {
        "name": "Florent",
        "linear_id": "2d4380e4-1894-4ee8-95c8-f07815d22bd8",
        "role": "General Partner",
        "domains": [
            "AI infrastructure", "inference", "model serving", "GPU orchestration",
            "cloud ML", "MLOps", "data centers", "AI security",
            "privacy-preserving computation", "LLM infrastructure",
        ],
        "description": "Infrastructure software growth investor. AI infrastructure, inference/serving, GPU orchestration.",
        "visible_pages": _GP_PAGES,
    },
    "etel": {
        "name": "Etel Friedmann",
        "linear_id": "64f45344-5b52-43b4-bb97-923665f35870",
        "role": "General Partner",
        "domains": [
            "developer tooling", "DevOps", "LLM routing", "release orchestration",
            "CI/CD", "platform engineering", "AI agents", "AI security",
            "LLM infrastructure",
        ],
        "description": "10+ years scaling developer-focused infra startups. Developer tooling, DevOps, LLM routing.",
        "visible_pages": _GP_PAGES,
    },
}

# Default for authenticated Lunar emails without a specific profile
_DEFAULT_PROFILE = {
    "name": None,  # filled from st.user.name at runtime
    "linear_id": None,
    "role": "General Partner",
    "domains": [],
    "description": "",
    "visible_pages": _GP_PAGES,
}

# Build lookup: email → profile (both @lunarventures.eu and @lunar.vc)
_EMAIL_MAP = {}
for _key, _prof in _PROFILES.items():
    _EMAIL_MAP[f"{_key}@lunarventures.eu"] = _prof
    _EMAIL_MAP[f"{_key}@lunar.vc"] = _prof


def all_profiles():
    """Return all known profiles as a dict of key → profile."""
    return dict(_PROFILES)


def get_profile(email, fallback_name=None):
    """Look up a user profile by email.

    Returns the matching profile or a default profile for unknown Lunar emails.
    The returned dict is a copy safe to mutate (e.g., merging extra_domains).
    """
    profile = _EMAIL_MAP.get(email.lower())
    if profile:
        return dict(profile)
    # Unknown email — return default with name filled in
    result = dict(_DEFAULT_PROFILE)
    result["name"] = fallback_name or email.split("@")[0].title()
    return result
