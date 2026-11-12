"""
Deterministic Synthetic Data Generator for Compensation Equity and Disparity Analysis System.
Generates master, transactional, and event records with strict ID conventions and referential integrity.
Configurable for 'starter' (100 employees) and 'full' (5,000 employees) scales with fixed seed 20261022.
"""
from datetime import date, datetime, timedelta
import random
import json
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd

from src.config import RANDOM_SEED
from src.generator.seed_data import (
    LOCATIONS_SEED, LEVELS_SEED, ROLES_SEED,
    JOB_FAMILY_BASE_SALARY, LEVEL_RANK_MULTIPLIERS,
    EXCHANGE_RATES_SEED, ROLE_COMPARABILITY_SEED
)
from src.generator.edge_case_injector import EdgeCaseInjector


FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Margaret", "Anthony", "Betty", "Donald", "Sandra", "Mark", "Ashley",
    "Paul", "Dorothy", "Steven", "Kimberly", "Andrew", "Emily", "Kenneth", "Donna",
    "Joshua", "Michelle", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Edward", "Deborah", "Ronald", "Stephanie", "Timothy", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Shirley", "Eric", "Angela", "Jonathan", "Helen", "Stephen", "Anna",
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Nicole", "Brandon", "Emma",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Gregory", "Christine", "Frank", "Debra",
    "Alexander", "Rachel", "Raymond", "Catherine", "Patrick", "Carolyn", "Jack", "Janet",
    "Dennis", "Ruth", "Jerry", "Maria", "Tyler", "Heather", "Aaron", "Diane"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz", "Parker",
    "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales", "Murphy",
    "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson", "Bailey",
    "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward", "Richardson",
    "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray", "Mendoza",
    "Ruiz", "Hughes", "Price", "Alvarez", "Castillo", "Sanders", "Patel", "Myers",
    "Long", "Ross", "Foster", "Jimenez", "Powell", "Jenkins", "Perry", "Russell"
]


class SyntheticDataGenerator:
    """Generates complete, self-consistent compensation and HR datasets."""

    def __init__(self, seed: int = RANDOM_SEED, scale: str = "starter"):
        self.seed = seed
        self.scale = scale.lower()
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        if self.scale == "full":
            self.employee_count = 5000
            self.anomalies_count = 25
        else:
            self.employee_count = 100
            self.anomalies_count = 3

    def generate_all(self) -> Dict[str, Any]:
        """
        Executes generation sequence:
        1. Roles, levels, locations.
        2. Compensation bands.
        3. Employees.
        4. Salary records.
        5. Performance evidence.
        6. Tenure records.
        7. Promotions.
        8. Adjustment proposals.
        9. Approval events.
        10. Ground-truth labels.
        """
        # Reset seed for reproducibility
        self.rng.seed(self.seed)
        self.np_rng = np.random.default_rng(self.seed)

        # 1. Master records
        
        # 1. Master records
        locations = [dict(loc) for loc in LOCATIONS_SEED]
        levels = [dict(lvl) for lvl in LEVELS_SEED]
        # Use all job families so the dashboard shows all 35 roles
        roles = [dict(r) for r in ROLES_SEED]
        exchange_rates = [dict(fx) for fx in EXCHANGE_RATES_SEED]
        role_rationales = [dict(rcr) for rcr in ROLE_COMPARABILITY_SEED]


        # 2. Compensation bands (2024, 2025, 2026)
        compensation_bands = self._generate_compensation_bands(roles, levels, locations)

        # 3. Employees
        employees = self._generate_employees(roles, levels, locations)

        # 4. Salary records (3 years: 2024, 2025, 2026)
        salary_records = self._generate_salary_records(employees, compensation_bands, exchange_rates)

        # 5. Performance evidence (2024-H1, 2024-H2, 2025-H1, 2025-H2)
        performance_evidence = self._generate_performance_evidence(employees)

        # 6. Tenure records
        tenure_records = self._generate_tenure_records(employees)

        # 7. Promotions
        promotions = self._generate_promotions(employees, levels, roles)

        # 8. Adjustment proposals & Approval events
        proposals, approval_events = self._generate_proposals_and_events(
            employees,
            salary_records,
            compensation_bands=compensation_bands,
            roles=roles,
            levels=levels,
            locations=locations,
        )

        # 9. Inject 5 Mandatory Edge Cases + Deliberate Disparities & generate Ground Truth
        (
            salary_records,
            proposals,
            ground_truth,
            compensation_bands
        ) = EdgeCaseInjector.inject_edge_cases(
            employees=employees,
            salary_records=salary_records,
            compensation_bands=compensation_bands,
            proposals=proposals,
            approval_events=approval_events,
            performances=performance_evidence,
            role_rationales=role_rationales,
            num_anomalies_each=self.anomalies_count
        )

        # Append baseline non-anomalies to ground truth
        for emp in employees:
            if not any(gt["record_id"] == emp["employee_id"] for gt in ground_truth):
                ground_truth.append({
                    "ground_truth_id": f"GT-BASE-{emp['employee_id']}",
                    "record_type": "EMPLOYEE",
                    "record_id": emp["employee_id"],
                    "issue_type": "VALID_BASELINE",
                    "is_anomaly": False,
                    "expected_detection": "VALID",
                    "root_cause_explanation": "Valid baseline employee record conforming to compensation guidelines.",
                    "injected_at": "2026-01-01T00:00:00"
                })

        return {
            "locations": locations,
            "levels": levels,
            "roles": roles,
            "compensation_bands": compensation_bands,
            "employees": employees,
            "salary_records": salary_records,
            "performance_evidence": performance_evidence,
            "tenure_records": tenure_records,
            "promotions": promotions,
            "adjustment_proposals": proposals,
            "approval_events": approval_events,
            "exchange_rates": exchange_rates,
            "role_comparability_rationales": role_rationales,
            "ground_truth_records": ground_truth
        }

    def _generate_compensation_bands(
        self,
        roles: List[Dict],
        levels: List[Dict],
        locations: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generates effective-dated compensation bands for 2024, 2025, 2026."""
        bands = []
        years = [2024, 2025, 2026]

        for year in years:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"
            status = "EXPIRED" if year < 2026 else "ACTIVE"

            for role in roles:
                base_usd = JOB_FAMILY_BASE_SALARY.get(role["job_family"], 80000.0)

                for level in levels:
                    level_mult = LEVEL_RANK_MULTIPLIERS.get(level["rank"], 1.0)

                    for loc in locations:
                        col_idx = loc["cost_of_living_index"]
                        curr = loc["currency"]

                        # Find exchange rate for year
                        fx = 1.0
                        for r in EXCHANGE_RATES_SEED:
                            if r["from_currency"] == curr and r["effective_start_date"].startswith(str(year)):
                                fx = r["rate"]
                                break

                        # Calculate midpoint in local currency
                        midpoint_usd = base_usd * level_mult * col_idx
                        # Adjust for year-over-year merit inflation (3% per year)
                        year_factor = 1.0 + (year - 2024) * 0.03
                        midpoint_usd *= year_factor

                        # Convert midpoint to local currency
                        midpoint_local = midpoint_usd / fx

                        # Band range: min = 80% of mid, max = 120% of mid
                        min_sal = round(midpoint_local * 0.80, -2)
                        mid_sal = round(midpoint_local, -2)
                        max_sal = round(midpoint_local * 1.20, -2)

                        band_id = f"BAND-{role['role_id']}-{level['level_id']}-{loc['location_id']}-{year}"
                        bands.append({
                            "band_id": band_id,
                            "role_id": role["role_id"],
                            "level_id": level["level_id"],
                            "location_id": loc["location_id"],
                            "currency": curr,
                            "min_salary": min_sal,
                            "mid_salary": mid_sal,
                            "max_salary": max_sal,
                            "effective_start_date": start_date,
                            "effective_end_date": end_date,
                            "status": status
                        })
        return bands

    def _generate_employees(
        self,
        roles: List[Dict],
        levels: List[Dict],
        locations: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generates deterministic employee master records."""
        employees = []
        base_hire_start = date(2015, 1, 1)

        for i in range(1, self.employee_count + 1):
            emp_id = f"EMP-{i:06d}"
            fn = self.rng.choice(FIRST_NAMES)
            ln = self.rng.choice(LAST_NAMES)
            email = f"{fn.lower()}.{ln.lower()}.{i:06d}@company.org"

            # Assign role, level, location
            role = self.rng.choice(roles)
            dept = role["job_family"]

            # Realistic level distribution: pyramid structure (L1=20%, L2=35%, L3=25%, L4=12%, L5=6%, L6=2%)
            level_weights = [0.20, 0.35, 0.25, 0.12, 0.06, 0.02]
            level = self.rng.choices(levels, weights=level_weights, k=1)[0]

            # Location distribution: auto-weighted by cost_of_living_index (higher CoL = more employees)
            loc_weights = [loc.get("cost_of_living_index", 0.5) for loc in locations]
            location = self.rng.choices(locations, weights=loc_weights, k=1)[0]

            # Hire date between 2015 and 2025
            hire_offset_days = self.rng.randint(0, 365 * 10)
            hire_date = base_hire_start + timedelta(days=hire_offset_days)
            if hire_date > date(2025, 12, 31):
                hire_date = date(2025, 11, 15)

            # Employment type: 90% full-time, 10% part-time
            is_part_time = self.rng.random() < 0.10
            emp_type = "PART_TIME" if is_part_time else "FULL_TIME"
            fte = self.rng.choice([0.5, 0.6, 0.8]) if is_part_time else 1.0

            employees.append({
                "employee_id": emp_id,
                "first_name": fn,
                "last_name": ln,
                "email": email,
                "department": dept,
                "current_role_id": role["role_id"],
                "current_level_id": level["level_id"],
                "current_location_id": location["location_id"],
                "hire_date": hire_date.isoformat(),
                "employment_type": emp_type,
                "fte": fte,
                "is_active": True,
                "created_at": datetime(hire_date.year, hire_date.month, hire_date.day, 9, 0).isoformat(),
                "updated_at": datetime(2026, 1, 1, 10, 0).isoformat()
            })
        return employees

    def _generate_salary_records(
        self,
        employees: List[Dict],
        bands: List[Dict],
        exchange_rates: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generates 3 years of salary records (2024, 2025, 2026) for each employee."""
        salary_records = []
        # Pre-index bands: (role_id, level_id, location_id, year) -> band
        band_lookup = {}
        for b in bands:
            yr = int(b["effective_start_date"][:4])
            key = (b["role_id"], b["level_id"], b["location_id"], yr)
            band_lookup[key] = b

        # Pre-index exchange rates: (from_currency, year) -> rate
        fx_lookup = {}
        for fx in exchange_rates:
            yr = int(fx["effective_start_date"][:4])
            fx_lookup[(fx["from_currency"], yr)] = fx["rate"]

        years = [2024, 2025, 2026]

        for emp in employees:
            hire_year = int(emp["hire_date"][:4])
            emp_id = emp["employee_id"]

            for yr in years:
                # Employee must be hired by this year to have a record
                if hire_year > yr:
                    continue

                eff_date = f"{yr}-01-01"
                if hire_year == yr:
                    eff_date = emp["hire_date"]

                sal_id = f"SAL-{emp_id}-{yr}-01"

                band = band_lookup.get((emp["current_role_id"], emp["current_level_id"], emp["current_location_id"], yr))
                if not band:
                    mid_sal = 100000.0
                    curr = "USD"
                else:
                    mid_sal = band["mid_salary"]
                    curr = band["currency"]

                fx_rate = fx_lookup.get((curr, yr), 1.0)

                # Realistic salary variance around band midpoint: Gaussian ~ N(mid, 0.08*mid)
                variation_factor = self.np_rng.normal(1.0, 0.08)
                variation_factor = max(0.82, min(1.18, variation_factor))

                # Full-time equivalent base in local currency:
                fte_base = mid_sal * variation_factor

                # Actual local base salary scales by employee FTE
                actual_base_local = round(fte_base * emp["fte"], -2)

                # Normalized salary in USD (at 1.0 FTE):
                annual_usd = (actual_base_local * fx_rate)
                norm_salary = round(annual_usd / emp["fte"], 2)

                reason = "HIRE" if hire_year == yr else ("ANNUAL_MERIT" if yr != 2026 else "MARKET_ADJUSTMENT")

                end_date = f"{yr}-12-31" if yr < 2026 else None

                salary_records.append({
                    "salary_id": sal_id,
                    "employee_id": emp_id,
                    "base_salary": actual_base_local,
                    "currency": curr,
                    "fte": emp["fte"],
                    "pay_frequency": "ANNUAL",
                    "normalized_salary": norm_salary,
                    "normalized_currency": "USD",
                    "effective_date": eff_date,
                    "end_date": end_date,
                    "change_reason": reason,
                    "benchmark_band_id": band["band_id"] if band else None,
                    "created_at": f"{eff_date}T09:00:00"
                })

        return salary_records

    def _generate_performance_evidence(self, employees: List[Dict]) -> List[Dict[str, Any]]:
        """Generates performance reviews across 4 cycles: 2024-H1, 2024-H2, 2025-H1, 2025-H2."""
        evidence = []
        cycles = [
            ("2024-H1", "2024-06-30"),
            ("2024-H2", "2024-12-31"),
            ("2025-H1", "2025-06-30"),
            ("2025-H2", "2025-12-31"),
        ]

        for emp in employees:
            hire_date = emp["hire_date"]
            emp_id = emp["employee_id"]

            for cycle_code, cycle_end_date in cycles:
                if hire_date > cycle_end_date:
                    continue

                # Rating distribution: 10% Needs Imp, 60% Meets, 25% Exceeds, 5% Outstanding
                score = round(float(self.np_rng.normal(3.4, 0.6)), 2)
                score = max(1.5, min(5.0, score))

                if score < 2.5:
                    label = "NEEDS_IMPROVEMENT"
                elif score < 3.7:
                    label = "MEETS_EXPECTATIONS"
                elif score < 4.5:
                    label = "EXCEEDS_EXPECTATIONS"
                else:
                    label = "OUTSTANDING"

                skills_score = round(float(self.np_rng.normal(75.0, 10.0)), 1)
                skills_score = max(40.0, min(100.0, skills_score))

                initiatives = self.rng.randint(0, 4)

                evidence_id = f"PERF-{emp_id}-{cycle_code}"
                evidence.append({
                    "evidence_id": evidence_id,
                    "employee_id": emp_id,
                    "review_cycle": cycle_code,
                    "rating_score": score,
                    "rating_label": label,
                    "reviewer_id": None,
                    "documented_skills_score": skills_score,
                    "critical_initiative_count": initiatives,
                    "effective_date": cycle_end_date
                })
        return evidence

    def _generate_tenure_records(self, employees: List[Dict]) -> List[Dict[str, Any]]:
        """Generates 1:1 tenure records as of 2026-01-01."""
        tenure = []
        as_of = date(2026, 1, 1)

        for emp in employees:
            emp_id = emp["employee_id"]
            hire_d = datetime.strptime(emp["hire_date"], "%Y-%m-%d").date()

            comp_tenure = max(0.1, round((as_of - hire_d).days / 365.25, 2))
            # Prior experience between 0 and 15 years
            prior_exp = round(float(self.rng.randint(0, 15)), 1)
            total_exp = round(comp_tenure + prior_exp, 2)
            role_tenure = max(0.1, round(comp_tenure * self.rng.uniform(0.6, 1.0), 2))

            tenure_id = f"TEN-{emp_id}"
            tenure.append({
                "tenure_id": tenure_id,
                "employee_id": emp_id,
                "company_start_date": emp["hire_date"],
                "role_start_date": emp["hire_date"],
                "years_of_experience_total": total_exp,
                "tenure_in_company_years": comp_tenure,
                "tenure_in_role_years": role_tenure
            })
        return tenure

    def _generate_promotions(
        self,
        employees: List[Dict],
        levels: List[Dict],
        roles: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Generates historical promotion events for ~15% of employees."""
        promotions = []
        level_map = {lvl["level_id"]: lvl for lvl in levels}

        for emp in employees:
            # 15% promotion chance if hired before 2024
            hire_yr = int(emp["hire_date"][:4])
            if hire_yr <= 2023 and self.rng.random() < 0.15:
                emp_id = emp["employee_id"]
                curr_lvl = level_map.get(emp["current_level_id"])
                if curr_lvl and curr_lvl["rank"] > 1:
                    from_rank = curr_lvl["rank"] - 1
                    from_lvl = next((l for l in levels if l["rank"] == from_rank), None)
                    if from_lvl:
                        prom_date = f"2025-07-01"
                        prev_sal = 110000.0
                        new_sal = 125000.0
                        inc_pct = round(((new_sal - prev_sal) / prev_sal) * 100.0, 2)

                        prom_id = f"PROM-{emp_id}-202507"
                        promotions.append({
                            "promotion_id": prom_id,
                            "employee_id": emp_id,
                            "from_level_id": from_lvl["level_id"],
                            "to_level_id": curr_lvl["level_id"],
                            "from_role_id": emp["current_role_id"],
                            "to_role_id": emp["current_role_id"],
                            "promotion_date": prom_date,
                            "previous_salary": prev_sal,
                            "new_salary": new_sal,
                            "increase_percentage": inc_pct,
                            "approved_by": "VP of Engineering / HR Committee"
                        })
        return promotions

    def _generate_proposals_and_events(
        self,
        employees: List[Dict],
        salary_records: List[Dict],
        compensation_bands: List[Dict] = None,
        roles: List[Dict] = None,
        levels: List[Dict] = None,
        locations: List[Dict] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Generates adjustment proposals with L6 reviewers, varied cycles, varied % adjustments, and all 5 reasons."""
        proposals = []
        approval_events = []
        event_counter = 0

        role_titles = {r["role_id"]: r["role_title"] for r in (roles or [])}
        level_names = {l["level_id"]: l["level_name"] for l in (levels or [])}
        loc_names = {loc["location_id"]: loc["location_name"] for loc in (locations or [])}

        # Index L6 Directors/Executives by (department, location) and by department for realistic reviewer assignment
        l6_all = [e for e in employees if e["current_level_id"] == "LVL-L6"]
        l6_by_dept_loc: Dict[Tuple[str, str], List[str]] = {}
        l6_by_dept: Dict[str, List[str]] = {}
        for mgr in l6_all:
            l6_by_dept_loc.setdefault((mgr["department"], mgr["current_location_id"]), []).append(mgr["email"])
            l6_by_dept.setdefault(mgr["department"], []).append(mgr["email"])
        fallback_reviewers = [m["email"] for m in l6_all] or ["jane.doe.vp@company.org"]

        # Index latest 2026 normalized salary per employee
        latest_sal_by_emp: Dict[str, float] = {}
        for s in salary_records:
            latest_sal_by_emp[s["employee_id"]] = float(s["normalized_salary"])

        # Create proposals for 5% of employees
        proposal_count = max(5, int(len(employees) * 0.05))
        sample_employees = self.rng.sample(employees, proposal_count)

        statuses = ["APPROVED", "APPROVED", "PENDING_REVIEW", "REJECTED", "DRAFT"]
        reason_codes = [
            "INTERNAL_EQUITY",
            "MARKET_PARITY",
            "DISPARITY_CORRECTION",
            "PROMOTION_CATCHUP",
            "RETENTION",
        ]
        # Varied effective dates & cycle timelines (created_date, submitted_date, reviewed_date, effective_date)
        cycles = [
            ("2025-08-18", "2025-08-20", "2025-09-02", "2025-10-01"),
            ("2025-11-12", "2025-11-14", "2025-11-28", "2026-01-01"),
            ("2026-02-15", "2026-02-17", "2026-02-28", "2026-04-01"),
            ("2026-05-14", "2026-05-16", "2026-05-29", "2026-07-01"),
            ("2026-08-19", "2026-08-21", "2026-09-04", "2026-10-01"),
        ]
        hr_creators = {
            "LOC-NYC": "hr.americas@company.org",
            "LOC-SFO": "hr.americas@company.org",
            "LOC-TOR": "hr.americas@company.org",
            "LOC-SAO": "hr.americas@company.org",
            "LOC-LON": "hr.emea@company.org",
            "LOC-BER": "hr.emea@company.org",
            "LOC-AMS": "hr.emea@company.org",
            "LOC-WAR": "hr.emea@company.org",
            "LOC-DXB": "hr.emea@company.org",
            "LOC-BLR": "hr.apac@company.org",
            "LOC-TYO": "hr.apac@company.org",
            "LOC-SIN": "hr.apac@company.org",
            "LOC-SYD": "hr.apac@company.org",
            "LOC-SEO": "hr.apac@company.org",
        }

        for i, emp in enumerate(sample_employees, 1):
            prop_id = f"ADJ-2026-{i:06d}"
            emp_id = emp["employee_id"]
            dept = emp["department"]
            r_title = role_titles.get(emp["current_role_id"], emp["current_role_id"])
            l_name = level_names.get(emp["current_level_id"], emp["current_level_id"])
            c_name = loc_names.get(emp["current_location_id"], emp["current_location_id"])

            curr_sal = latest_sal_by_emp.get(emp_id, 100000.0)
            reason_code = reason_codes[(i - 1) % len(reason_codes)]

            # Varied, realistic adjustment % by reason (including downward market-cap / red-circle alignments across all statuses)
            if reason_code == "DISPARITY_CORRECTION":
                pct_delta = round(self.rng.uniform(0.10, 0.24), 4)
            elif reason_code == "PROMOTION_CATCHUP":
                pct_delta = round(self.rng.uniform(0.08, 0.19), 4)
            elif reason_code == "INTERNAL_EQUITY":
                if self.rng.random() < 0.18:
                    pct_delta = round(-self.rng.uniform(0.02, 0.07), 4)
                else:
                    pct_delta = round(self.rng.uniform(0.05, 0.16), 4)
            elif reason_code == "RETENTION":
                pct_delta = round(self.rng.uniform(0.04, 0.15), 4)
            else:  # MARKET_PARITY (mix of upward calibrations +4%..+14% and downward market-cap alignments -2%..-10%)
                if self.rng.random() < 0.35:
                    pct_delta = round(-self.rng.uniform(0.02, 0.10), 4)
                else:
                    pct_delta = round(self.rng.uniform(0.04, 0.14), 4)

            prop_sal = round(curr_sal * (1.0 + pct_delta), 2)
            adj_amt = round(prop_sal - curr_sal, 2)
            adj_pct = round((adj_amt / curr_sal) * 100.0, 2) if curr_sal > 0 else 0.0

            status = statuses[i % len(statuses)]
            c_date, s_date, r_date, eff_date = cycles[i % len(cycles)]
            created_dt = f"{c_date}T09:30:00"
            submitted_dt = f"{s_date}T11:00:00"
            rev_dt = f"{r_date}T14:15:00" if status in ["APPROVED", "REJECTED"] else None

            # Select reviewer from L6 Directors/Executives (matched by department+location, then department)
            pool = (
                l6_by_dept_loc.get((dept, emp["current_location_id"]))
                or l6_by_dept.get(dept)
                or fallback_reviewers
            )
            # Avoid self-review if the employee is L6
            eligible_pool = [m for m in pool if m != emp["email"]] or fallback_reviewers
            reviewer = self.rng.choice(eligible_pool) if status in ["APPROVED", "REJECTED"] else None
            creator = hr_creators.get(emp["current_location_id"], "hr.partner@company.org")

            justification_map = {
                "INTERNAL_EQUITY": (
                    f"Internal peer parity adjustment ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"to align compensation with comparable peer cohort median."
                ),
                "MARKET_PARITY": (
                    f"Downward market-cap realignment ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"to bring above-ceiling compensation back within the regional band maximum."
                    if adj_pct < 0
                    else f"Market band calibration ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"to maintain competitive positioning against the regional band midpoint."
                ),
                "DISPARITY_CORRECTION": (
                    f"Equity disparity remediation ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"following strong performance reviews and established tenure."
                ),
                "PROMOTION_CATCHUP": (
                    f"Post-promotion band catch-up ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"to move compensation out of the entry quartile of the new level."
                ),
                "RETENTION": (
                    f"Critical talent retention adjustment ({adj_pct:+.1f}%) for {r_title} ({l_name}) in {c_name} "
                    f"recognizing sustained high performance and critical initiative delivery."
                ),
            }
            if status == "APPROVED":
                rev_note = f"Approved by {dept} L6 leadership for {eff_date} payroll cycle after cohort and budget validation."
            elif status == "REJECTED":
                rev_note = f"Deferred by {dept} L6 leadership pending next performance cycle and regional budget allocation."
            else:
                rev_note = None

            proposals.append({
                "proposal_id": prop_id,
                "employee_id": emp_id,
                "current_salary": curr_sal,
                "proposed_salary": prop_sal,
                "adjustment_amount": adj_amt,
                "adjustment_percentage": adj_pct,
                "reason_code": reason_code,
                "justification_notes": justification_map[reason_code],
                "evidence_summary": json.dumps({"performance_rating": round(self.rng.uniform(3.4, 4.9), 2), "tenure_years": round(self.rng.uniform(1.2, 8.5), 1)}),
                "related_disparity_findings": json.dumps({"compa_ratio": round(self.rng.uniform(0.74, 1.05), 2), "cohort_deviation": round(self.rng.uniform(-22.0, 5.0), 1)}),
                "proposed_effective_date": eff_date,
                "approval_status": status,
                "created_by": creator,
                "created_at": created_dt,
                "reviewed_by": reviewer,
                "reviewed_at": rev_dt,
                "review_notes": rev_note,
            })

            # Audit event 1: CREATED
            event_counter += 1
            approval_events.append({
                "event_id": f"EVT-{c_date.replace('-', '')}-{event_counter:06d}",
                "entity_name": "AdjustmentProposal",
                "entity_id": prop_id,
                "event_type": "PROPOSAL_CREATED",
                "actor_id": creator,
                "actor_role": "HR_PARTNER",
                "old_state": None,
                "new_state": json.dumps({"status": "DRAFT", "proposed_salary": prop_sal, "reason": reason_code}),
                "notes": f"Initial {reason_code.replace('_', ' ').title()} proposal drafted for {emp_id} ({r_title}).",
                "timestamp": created_dt
            })

            # Audit event 2: SUBMITTED (if not draft)
            if status != "DRAFT":
                event_counter += 1
                approval_events.append({
                    "event_id": f"EVT-{s_date.replace('-', '')}-{event_counter:06d}",
                    "entity_name": "AdjustmentProposal",
                    "entity_id": prop_id,
                    "event_type": "SUBMITTED_FOR_REVIEW",
                    "actor_id": creator,
                    "actor_role": "HR_PARTNER",
                    "old_state": json.dumps({"status": "DRAFT"}),
                    "new_state": json.dumps({"status": "PENDING_REVIEW"}),
                    "notes": f"Submitted for {dept} executive compensation review.",
                    "timestamp": submitted_dt
                })

            # Audit event 3: REVIEW DECISION
            if status in ["APPROVED", "REJECTED"]:
                event_counter += 1
                approval_events.append({
                    "event_id": f"EVT-{r_date.replace('-', '')}-{event_counter:06d}",
                    "entity_name": "AdjustmentProposal",
                    "entity_id": prop_id,
                    "event_type": f"PROPOSAL_{status}",
                    "actor_id": reviewer,
                    "actor_role": "MANAGER",
                    "old_state": json.dumps({"status": "PENDING_REVIEW"}),
                    "new_state": json.dumps({"status": status}),
                    "notes": rev_note,
                    "timestamp": rev_dt
                })

        return proposals, approval_events
