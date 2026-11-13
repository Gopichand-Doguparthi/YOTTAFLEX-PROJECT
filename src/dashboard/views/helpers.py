"""
Shared lookup, caching, and formatting helpers for dashboard views.
Provides ID-to-name resolution, cached SQL snapshots for fast tab switching,
USD band conversion, and clean non-overlapping Plotly layouts.
"""
from typing import Tuple, Optional, Dict, Any
import streamlit as st
from sqlalchemy.orm import Session
from src.database.session import SessionLocal
from src.engine.currency_normalizer import CurrencyNormalizer


@st.cache_data(ttl=300, show_spinner=False)
def load_reference_catalogs() -> Dict[str, Any]:
    """Loads Role, Level, and Location catalogs once and caches them for fast sidebar/view rendering."""
    from src.database.models import Role, Level, Location
    db = SessionLocal()
    try:
        roles = [(r.role_id, r.role_title) for r in db.query(Role.role_id, Role.role_title).order_by(Role.role_title).all()]
        levels = [(l.level_id, l.level_name, l.level_code, l.rank) for l in db.query(Level.level_id, Level.level_name, Level.level_code, Level.rank).order_by(Level.rank).all()]
        locs = [(loc.location_id, loc.location_name) for loc in db.query(Location.location_id, Location.location_name).order_by(Location.location_name).all()]
        return {
            "roles_list": roles,
            "levels_list": levels,
            "locs_list": locs,
            "role_map": {rid: title for rid, title in roles},
            "level_map": {lid: f"{name} ({code})" for lid, name, code, _ in levels},
            "loc_map": {loc_id: name for loc_id, name in locs},
        }
    finally:
        db.close()


def get_role_map(db: Session = None) -> dict:
    """Returns {role_id: role_title}."""
    return load_reference_catalogs()["role_map"]


def get_level_map(db: Session = None) -> dict:
    """Returns {level_id: 'Level Name (Code)'}."""
    return load_reference_catalogs()["level_map"]


def get_location_map(db: Session = None) -> dict:
    """Returns {location_id: location_name}."""
    return load_reference_catalogs()["loc_map"]


@st.cache_data(ttl=300, show_spinner=False)
def load_fx_rates_list() -> list:
    """Loads and caches exchange rate rows as lightweight dicts."""
    from src.database.models import ExchangeRate
    db = SessionLocal()
    try:
        rows = db.query(ExchangeRate).all()
        return [
            {
                "from_currency": r.from_currency,
                "to_currency": r.to_currency,
                "rate": float(r.rate),
                "effective_start_date": r.effective_start_date,
                "effective_end_date": r.effective_end_date,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_currency_normalizer(db: Session = None) -> CurrencyNormalizer:
    """Builds a CurrencyNormalizer using cached exchange rates."""
    return CurrencyNormalizer(rates=load_fx_rates_list())


def get_band_usd_amounts(band, curr_norm: CurrencyNormalizer) -> Tuple[float, float, float]:
    """Converts a CompensationBand's min/mid/max salaries from local currency to USD."""
    curr = band["currency"] if isinstance(band, dict) else band.currency
    b_min = band["min_salary"] if isinstance(band, dict) else band.min_salary
    b_mid = band["mid_salary"] if isinstance(band, dict) else band.mid_salary
    b_max = band["max_salary"] if isinstance(band, dict) else band.max_salary
    eff = band["effective_start_date"] if isinstance(band, dict) else band.effective_start_date

    if curr == "USD":
        return float(b_min), float(b_mid), float(b_max)
    try:
        rate = curr_norm.get_rate(curr, "USD", eff)
    except Exception:
        rate = 1.0
    return (
        round(float(b_min) * rate, 2),
        round(float(b_mid) * rate, 2),
        round(float(b_max) * rate, 2),
    )


def fmt_usd(val: Optional[float]) -> str:
    """Format a USD currency amount cleanly with commas (no invalid printf format)."""
    if val is None:
        return "$0"
    return f"${val:,.0f}"


def fmt_num(val: Optional[float], decimals: int = 0) -> str:
    """Format a numeric amount cleanly with commas."""
    if val is None:
        return "0"
    return f"{val:,.{decimals}f}"


def fmt_pct(val: Optional[float], decimals: int = 1, signed: bool = False) -> str:
    """Format a percentage cleanly."""
    if val is None:
        return "0.0%"
    if signed:
        return f"{val:+.{decimals}f}%"
    return f"{val:.{decimals}f}%"


_ACRONYMS = {"hr", "vp", "ceo", "cfo", "cto", "coo", "ai", "ml", "it", "id", "americas", "emea", "apac"}

CURRENCY_NAMES = {
    "USD": "US Dollar",
    "GBP": "British Pound",
    "EUR": "Euro",
    "INR": "Indian Rupee",
    "JPY": "Japanese Yen",
    "SGD": "Singapore Dollar",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "AED": "UAE Dirham",
    "BRL": "Brazilian Real",
    "PLN": "Polish Zloty",
    "KRW": "South Korean Won",
}


def format_currency_label(code: str) -> str:
    """Returns 'CODE — Full Currency Name' for dropdowns."""
    name = CURRENCY_NAMES.get(code)
    return f"{code} — {name}" if name else code


def format_actor_name(actor: Optional[str], fallback: str = "Pending") -> str:
    """Formats an actor email or ID (e.g. 'james.smith.000123@company.org') into a readable name."""
    if not actor or not str(actor).strip():
        return fallback
    raw = str(actor).strip()
    if "@" not in raw:
        return raw
    local = raw.split("@", 1)[0]
    tokens = [t for t in local.replace("_", ".").replace("-", ".").split(".") if t]
    if not tokens:
        return raw

    # Strip trailing numeric employee-ID suffix (e.g. '000123')
    if len(tokens) >= 2 and tokens[-1].isdigit():
        tokens = tokens[:-1]

    title_suffix = ""
    if len(tokens) >= 3 and tokens[-1].lower() in {"vp", "ceo", "cfo", "cto", "coo"}:
        title_suffix = f" ({tokens[-1].upper()})"
        tokens = tokens[:-1]

    formatted_tokens = [
        t.upper() if t.lower() in _ACRONYMS else t.capitalize()
        for t in tokens
    ]
    return " ".join(formatted_tokens) + title_suffix


def resolve(id_val: str, lookup: dict) -> str:
    """Resolve an ID to its name, returning original if not found."""
    return lookup.get(id_val, id_val)


def map_col(df, col: str, lookup: dict, new_col: str = None):
    """Map a DataFrame column of IDs to human names in-place."""
    target = new_col or col
    df[target] = df[col].map(lambda x: lookup.get(x, x))
    return df


PLOTLY_CONFIG = {
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    "responsive": True,
}


def apply_clean_layout(
    fig,
    legend_bottom: bool = True,
    height: int = 450,
    xaxis_tickangle: int = 0,
    extra_bottom_margin: int = 0,
    legend_position: str = "top",
):
    """
    Applies clean layout settings without title/canvas collision.
    Supports both Cartesian (bar/line/scatter) and polar/pie figures.
    """
    top_margin = 85 if legend_bottom and legend_position == "top" else 65
    bottom_margin = (75 if legend_bottom and legend_position == "bottom" else 55) + extra_bottom_margin

    is_pie = bool(fig.data and getattr(fig.data[0], "type", "") == "pie")

    layout_kwargs = dict(
        uirevision="preserve",
        transition={"duration": 0},
        hovermode="closest" if not is_pie else False,
        height=height,
        title=dict(
            x=0.0,
            xanchor="left",
            font=dict(size=15),
        ),
        modebar=dict(
            orientation="h",
            bgcolor="rgba(15, 23, 42, 0.78)",
            color="#cbd5e1",
            activecolor="#818cf8",
        ),
        margin=dict(t=top_margin, b=bottom_margin, l=60, r=30),
    )
    if not is_pie:
        layout_kwargs["xaxis"] = dict(
            automargin=True,
            title_standoff=14,
            tickfont=dict(size=12),
            tickangle=xaxis_tickangle,
        )
        layout_kwargs["yaxis"] = dict(
            automargin=True,
            title_standoff=10,
        )

    if legend_bottom:
        if legend_position == "top":
            layout_kwargs["legend"] = dict(
                title_text="",
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0.0,
                font=dict(size=12),
            )
        else:
            layout_kwargs["legend"] = dict(
                title_text="",
                orientation="h",
                yanchor="top",
                y=-0.12,
                xanchor="center",
                x=0.5,
                font=dict(size=12),
            )
    fig.update_layout(**layout_kwargs)
    return fig


def build_table_column_config(df, overrides: dict = None) -> dict:
    """
    Lets Streamlit auto-size columns tightly to their exact cell contents (width=None)
    and only expands genuinely long multi-sentence text columns (> 55 chars) so
    short/medium columns never have wasted whitespace.
    """
    cfg = {}
    for col in df.columns:
        if overrides and col in overrides:
            cfg[col] = overrides[col]
            continue
        max_cell = int(df[col].astype(str).str.len().max()) if not df.empty else 0
        if max_cell > 55:
            cfg[col] = st.column_config.TextColumn(col, width="large")
    return cfg
