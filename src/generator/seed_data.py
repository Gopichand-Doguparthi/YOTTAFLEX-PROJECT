"""
Master Seed Definitions and Reference Catalogs for Synthetic Data Generation.
Provides standardized Roles, Levels, Locations, Currencies, and Exchange Rates.
"""

# 14 Global Locations with realistic Cost-of-Living indices and primary currencies
LOCATIONS_SEED = [
    {
        "location_id": "LOC-NYC",
        "location_name": "New York City, USA",
        "country": "USA",
        "currency": "USD",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 1.00
    },
    {
        "location_id": "LOC-SFO",
        "location_name": "San Francisco, USA",
        "country": "USA",
        "currency": "USD",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 1.15
    },
    {
        "location_id": "LOC-LON",
        "location_name": "London, United Kingdom",
        "country": "GBR",
        "currency": "GBP",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 0.95
    },
    {
        "location_id": "LOC-BER",
        "location_name": "Berlin, Germany",
        "country": "DEU",
        "currency": "EUR",
        "geo_tier": "Tier-2",
        "cost_of_living_index": 0.80
    },
    {
        "location_id": "LOC-BLR",
        "location_name": "Bengaluru, India",
        "country": "IND",
        "currency": "INR",
        "geo_tier": "Tier-3",
        "cost_of_living_index": 0.35
    },
    {
        "location_id": "LOC-TYO",
        "location_name": "Tokyo, Japan",
        "country": "JPN",
        "currency": "JPY",
        "geo_tier": "Tier-2",
        "cost_of_living_index": 0.85
    },
    {
        "location_id": "LOC-SIN",
        "location_name": "Singapore",
        "country": "SGP",
        "currency": "SGD",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 1.05
    },
    {
        "location_id": "LOC-AMS",
        "location_name": "Amsterdam, Netherlands",
        "country": "NLD",
        "currency": "EUR",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 0.92
    },
    {
        "location_id": "LOC-SYD",
        "location_name": "Sydney, Australia",
        "country": "AUS",
        "currency": "AUD",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 0.90
    },
    {
        "location_id": "LOC-TOR",
        "location_name": "Toronto, Canada",
        "country": "CAN",
        "currency": "CAD",
        "geo_tier": "Tier-1",
        "cost_of_living_index": 0.88
    },
    {
        "location_id": "LOC-DXB",
        "location_name": "Dubai, United Arab Emirates",
        "country": "ARE",
        "currency": "AED",
        "geo_tier": "Tier-2",
        "cost_of_living_index": 0.82
    },
    {
        "location_id": "LOC-SAO",
        "location_name": "São Paulo, Brazil",
        "country": "BRA",
        "currency": "BRL",
        "geo_tier": "Tier-3",
        "cost_of_living_index": 0.45
    },
    {
        "location_id": "LOC-WAR",
        "location_name": "Warsaw, Poland",
        "country": "POL",
        "currency": "PLN",
        "geo_tier": "Tier-3",
        "cost_of_living_index": 0.55
    },
    {
        "location_id": "LOC-SEO",
        "location_name": "Seoul, South Korea",
        "country": "KOR",
        "currency": "KRW",
        "geo_tier": "Tier-2",
        "cost_of_living_index": 0.78
    }
]

# 6 Standard Professional Levels (L1 to L6)
LEVELS_SEED = [
    {"level_id": "LVL-L1", "level_code": "L1", "level_name": "Associate", "rank": 1},
    {"level_id": "LVL-L2", "level_code": "L2", "level_name": "Mid-Level", "rank": 2},
    {"level_id": "LVL-L3", "level_code": "L3", "level_name": "Senior", "rank": 3},
    {"level_id": "LVL-L4", "level_code": "L4", "level_name": "Staff / Lead", "rank": 4},
    {"level_id": "LVL-L5", "level_code": "L5", "level_name": "Principal", "rank": 5},
    {"level_id": "LVL-L6", "level_code": "L6", "level_name": "Director / Executive", "rank": 6},
]

# 35 Distinct Roles across 7 Job Families
# 35 roles * 6 levels = 210 unique role/level combinations (> 200 requirement!)
ROLES_SEED = [
    # Engineering
    {"role_id": "ROLE-SWE", "role_title": "Software Engineer", "job_family": "Engineering", "job_function": "Backend & Core Systems"},
    {"role_id": "ROLE-FSE", "role_title": "Full Stack Engineer", "job_family": "Engineering", "job_function": "Web Applications"},
    {"role_id": "ROLE-DEV", "role_title": "DevOps Engineer", "job_family": "Engineering", "job_function": "Cloud Infrastructure"},
    {"role_id": "ROLE-QAE", "role_title": "QA Automation Engineer", "job_family": "Engineering", "job_function": "Quality Assurance"},
    {"role_id": "ROLE-SEC", "role_title": "Security Engineer", "job_family": "Engineering", "job_function": "Cybersecurity"},
    {"role_id": "ROLE-SYS", "role_title": "Systems Architect", "job_family": "Engineering", "job_function": "Enterprise Architecture"},
    
    # Data & AI
    {"role_id": "ROLE-DS", "role_title": "Data Scientist", "job_family": "Data & AI", "job_function": "Statistical Modeling"},
    {"role_id": "ROLE-MLE", "role_title": "Machine Learning Engineer", "job_family": "Data & AI", "job_function": "ML Platforms"},
    {"role_id": "ROLE-DE", "role_title": "Data Engineer", "job_family": "Data & AI", "job_function": "Data Pipelines"},
    {"role_id": "ROLE-BI", "role_title": "Business Intelligence Analyst", "job_family": "Data & AI", "job_function": "Analytics & BI"},
    {"role_id": "ROLE-RES", "role_title": "AI Research Scientist", "job_family": "Data & AI", "job_function": "Deep Learning Research"},
    
    # Product
    {"role_id": "ROLE-PM", "role_title": "Product Manager", "job_family": "Product", "job_function": "Product Strategy"},
    {"role_id": "ROLE-TPM", "role_title": "Technical Program Manager", "job_family": "Product", "job_function": "Program Execution"},
    {"role_id": "ROLE-PO", "role_title": "Product Owner", "job_family": "Product", "job_function": "Agile Delivery"},
    {"role_id": "ROLE-GPM", "role_title": "Growth Product Manager", "job_family": "Product", "job_function": "User Acquisition"},
    
    # Design
    {"role_id": "ROLE-PD", "role_title": "Product Designer", "job_family": "Design", "job_function": "UI/UX Design"},
    {"role_id": "ROLE-UXR", "role_title": "UX Researcher", "job_family": "Design", "job_function": "User Insights"},
    {"role_id": "ROLE-CD", "role_title": "Content Designer", "job_family": "Design", "job_function": "UX Writing"},
    {"role_id": "ROLE-VIS", "role_title": "Visual Designer", "job_family": "Design", "job_function": "Brand & Graphic"},
    
    # Operations
    {"role_id": "ROLE-OPS", "role_title": "Operations Analyst", "job_family": "Operations", "job_function": "Business Operations"},
    {"role_id": "ROLE-CSM", "role_title": "Customer Success Manager", "job_family": "Operations", "job_function": "Client Retention"},
    {"role_id": "ROLE-SUP", "role_title": "Technical Support Specialist", "job_family": "Operations", "job_function": "Tier-2 Support"},
    {"role_id": "ROLE-LOG", "role_title": "Logistics Coordinator", "job_family": "Operations", "job_function": "Supply Chain"},
    {"role_id": "ROLE-FAC", "role_title": "Facilities Coordinator", "job_family": "Operations", "job_function": "Workplace Facilities"},
    
    # Finance
    {"role_id": "ROLE-FIN", "role_title": "Financial Analyst", "job_family": "Finance", "job_function": "Corporate FP&A"},
    {"role_id": "ROLE-ACC", "role_title": "Senior Accountant", "job_family": "Finance", "job_function": "General Ledger"},
    {"role_id": "ROLE-TRX", "role_title": "Treasury Analyst", "job_family": "Finance", "job_function": "Cash Management"},
    {"role_id": "ROLE-TAX", "role_title": "Tax Specialist", "job_family": "Finance", "job_function": "Corporate Tax"},
    {"role_id": "ROLE-AUD", "role_title": "Internal Auditor", "job_family": "Finance", "job_function": "Financial Audit"},

    # Human Resources
    {"role_id": "ROLE-REC", "role_title": "Talent Acquisition Partner", "job_family": "Human Resources", "job_function": "Recruiting"},
    {"role_id": "ROLE-HRP", "role_title": "HR Business Partner", "job_family": "Human Resources", "job_function": "Talent Strategy"},
    {"role_id": "ROLE-CMP", "role_title": "Compensation & Benefits Analyst", "job_family": "Human Resources", "job_function": "Total Rewards"},
    {"role_id": "ROLE-LND", "role_title": "Learning & Development Specialist", "job_family": "Human Resources", "job_function": "People Development"},
    {"role_id": "ROLE-PEO", "role_title": "People Operations Generalist", "job_family": "Human Resources", "job_function": "Employee Services"},
    {"role_id": "ROLE-ER", "role_title": "Employee Relations Specialist", "job_family": "Human Resources", "job_function": "Workplace Policy"}
]

# Baseline USD annual midpoint salaries for Level 1 by Job Family (in NYC baseline)
JOB_FAMILY_BASE_SALARY = {
    "Engineering": 105000.0,
    "Data & AI": 110000.0,
    "Product": 100000.0,
    "Design": 90000.0,
    "Finance": 85000.0,
    "Human Resources": 75000.0,
    "Operations": 70000.0
}

# Multiplier progression per level rank
LEVEL_RANK_MULTIPLIERS = {
    1: 1.0,    # L1: Associate
    2: 1.30,   # L2: Mid-Level
    3: 1.65,   # L3: Senior
    4: 2.10,   # L4: Staff
    5: 2.70,   # L5: Principal
    6: 3.50    # L6: Director
}

# Effective-dated Annual Exchange Rates (2024 to 2026) -> Multiplier to convert local to USD: USD = local * rate
EXCHANGE_RATES_SEED = [
    # 2024
    {"exchange_rate_id": "FX-USD-USD-2024", "from_currency": "USD", "to_currency": "USD", "rate": 1.00,    "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-GBP-USD-2024", "from_currency": "GBP", "to_currency": "USD", "rate": 1.28,    "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-EUR-USD-2024", "from_currency": "EUR", "to_currency": "USD", "rate": 1.08,    "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-INR-USD-2024", "from_currency": "INR", "to_currency": "USD", "rate": 0.0120,  "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-JPY-USD-2024", "from_currency": "JPY", "to_currency": "USD", "rate": 0.0068,  "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-SGD-USD-2024", "from_currency": "SGD", "to_currency": "USD", "rate": 0.74,    "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-AUD-USD-2024", "from_currency": "AUD", "to_currency": "USD", "rate": 0.655,   "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-CAD-USD-2024", "from_currency": "CAD", "to_currency": "USD", "rate": 0.740,   "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-AED-USD-2024", "from_currency": "AED", "to_currency": "USD", "rate": 0.272,   "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-BRL-USD-2024", "from_currency": "BRL", "to_currency": "USD", "rate": 0.200,   "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-PLN-USD-2024", "from_currency": "PLN", "to_currency": "USD", "rate": 0.248,   "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},
    {"exchange_rate_id": "FX-KRW-USD-2024", "from_currency": "KRW", "to_currency": "USD", "rate": 0.00075, "effective_start_date": "2024-01-01", "effective_end_date": "2024-12-31"},

    # 2025
    {"exchange_rate_id": "FX-USD-USD-2025", "from_currency": "USD", "to_currency": "USD", "rate": 1.00,    "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-GBP-USD-2025", "from_currency": "GBP", "to_currency": "USD", "rate": 1.30,    "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-EUR-USD-2025", "from_currency": "EUR", "to_currency": "USD", "rate": 1.10,    "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-INR-USD-2025", "from_currency": "INR", "to_currency": "USD", "rate": 0.0118,  "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-JPY-USD-2025", "from_currency": "JPY", "to_currency": "USD", "rate": 0.0065,  "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-SGD-USD-2025", "from_currency": "SGD", "to_currency": "USD", "rate": 0.75,    "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-AUD-USD-2025", "from_currency": "AUD", "to_currency": "USD", "rate": 0.645,   "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-CAD-USD-2025", "from_currency": "CAD", "to_currency": "USD", "rate": 0.735,   "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-AED-USD-2025", "from_currency": "AED", "to_currency": "USD", "rate": 0.272,   "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-BRL-USD-2025", "from_currency": "BRL", "to_currency": "USD", "rate": 0.185,   "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-PLN-USD-2025", "from_currency": "PLN", "to_currency": "USD", "rate": 0.252,   "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},
    {"exchange_rate_id": "FX-KRW-USD-2025", "from_currency": "KRW", "to_currency": "USD", "rate": 0.00073, "effective_start_date": "2025-01-01", "effective_end_date": "2025-12-31"},

    # 2026
    {"exchange_rate_id": "FX-USD-USD-2026", "from_currency": "USD", "to_currency": "USD", "rate": 1.00,    "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-GBP-USD-2026", "from_currency": "GBP", "to_currency": "USD", "rate": 1.32,    "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-EUR-USD-2026", "from_currency": "EUR", "to_currency": "USD", "rate": 1.09,    "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-INR-USD-2026", "from_currency": "INR", "to_currency": "USD", "rate": 0.0115,  "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-JPY-USD-2026", "from_currency": "JPY", "to_currency": "USD", "rate": 0.0066,  "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-SGD-USD-2026", "from_currency": "SGD", "to_currency": "USD", "rate": 0.76,    "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-AUD-USD-2026", "from_currency": "AUD", "to_currency": "USD", "rate": 0.650,   "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-CAD-USD-2026", "from_currency": "CAD", "to_currency": "USD", "rate": 0.738,   "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-AED-USD-2026", "from_currency": "AED", "to_currency": "USD", "rate": 0.272,   "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-BRL-USD-2026", "from_currency": "BRL", "to_currency": "USD", "rate": 0.178,   "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-PLN-USD-2026", "from_currency": "PLN", "to_currency": "USD", "rate": 0.255,   "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
    {"exchange_rate_id": "FX-KRW-USD-2026", "from_currency": "KRW", "to_currency": "USD", "rate": 0.00072, "effective_start_date": "2026-01-01", "effective_end_date": "2026-12-31"},
]

# Documented Role Comparability Rationales (Approved pairings)
ROLE_COMPARABILITY_SEED = [
    {
        "mapping_id": "RCR-SWE-FSE",
        "role_id_a": "ROLE-SWE",
        "role_id_b": "ROLE-FSE",
        "is_comparable": True,
        "documented_rationale": "Equivalent core software engineering competencies, architecture design requirements, and market salary bands.",
        "approved_by": "Compensation Committee",
        "effective_date": "2024-01-01"
    },
    {
        "mapping_id": "RCR-DS-MLE",
        "role_id_a": "ROLE-DS",
        "role_id_b": "ROLE-MLE",
        "is_comparable": True,
        "documented_rationale": "Overlapping machine learning foundations, algorithms, and computational data science requirements.",
        "approved_by": "Compensation Committee",
        "effective_date": "2024-01-01"
    },
    {
        "mapping_id": "RCR-PM-TPM",
        "role_id_a": "ROLE-PM",
        "role_id_b": "ROLE-TPM",
        "is_comparable": True,
        "documented_rationale": "Shared technical leadership, roadmap execution, and product lifecycle responsibilities.",
        "approved_by": "Compensation Committee",
        "effective_date": "2024-01-01"
    },
    {
        "mapping_id": "RCR-SWE-FAC",
        "role_id_a": "ROLE-SWE",
        "role_id_b": "ROLE-FAC",
        "is_comparable": False,
        "documented_rationale": "Incomparable roles: Software Engineering and Facilities Coordinator require fundamentally distinct skills and labor markets.",
        "approved_by": "HR Compliance",
        "effective_date": "2024-01-01"
    }
]
