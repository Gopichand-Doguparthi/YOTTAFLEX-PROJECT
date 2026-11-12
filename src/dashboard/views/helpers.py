"""
Shared lookup and formatting helpers for dashboard views.
Provides ID-to-name resolution for Role, Level, Location, Actor names,
USD band conversion, and consistent smooth-zoom Plotly styling.
"""
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from src.engine.currency_normalizer import CurrencyNormalizer


def get_role_map(db: Session) -> dict:
    """Returns {role_id: role_title}."""
    from src.database.models import Role
    return {r.role_id: r.role_title for r in db.query(Role).all()}


def get_level_map(db: Session) -> dict:
    """Returns {level_id: 'Level Name (Code)'}."""
    from src.database.models import Level
    return {l.level_id: f"{l.level_name} ({l.level_code})" for l in db.query(Level).all()}


def get_location_map(db: Session) -> dict:
    """Returns {location_id: location_name}."""
    from src.database.models import Location
    return {loc.location_id: loc.location_name for loc in db.query(Location).all()}


def get_currency_normalizer(db: Session) -> CurrencyNormalizer:
    """Loads exchange rates from DB into a CurrencyNormalizer instance."""
    cn = CurrencyNormalizer()
    cn.load_from_db(db)
    return cn


def get_band_usd_amounts(band, curr_norm: CurrencyNormalizer) -> Tuple[float, float, float]:
    """Converts a CompensationBand's min/mid/max salaries from local currency to USD."""
    if band.currency == "USD":
        return float(band.min_salary), float(band.mid_salary), float(band.max_salary)
    try:
        rate = curr_norm.get_rate(band.currency, "USD", band.effective_start_date)
    except Exception:
        rate = 1.0
    return (
        round(float(band.min_salary) * rate, 2),
        round(float(band.mid_salary) * rate, 2),
        round(float(band.max_salary) * rate, 2),
    )


_ACRONYMS = {"hr", "vp", "ceo", "cfo", "cto", "coo", "ai", "ml", "it", "id"}


def format_actor_name(actor: Optional[str], fallback: str = "Pending") -> str:
    """Formats an actor email or ID (e.g. 'jane.doe.vp@company.org') into a readable name."""
    if not actor or not str(actor).strip():
        return fallback
    raw = str(actor).strip()
    if "@" not in raw:
        return raw
    local = raw.split("@", 1)[0]
    tokens = [t for t in local.replace("_", ".").replace("-", ".").split(".") if t]
    if not tokens:
        return raw

    # Handle trailing title tokens like 'vp' or 'lead'
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
    height: int = 430,
    xaxis_tickangle: int = 0,
    extra_bottom_margin: int = 0,
):
    """
    Applies smooth-zoom layout settings so text never blinks during scroll zoom
    and legends/colorbars never collide with titles or annotations.
    """
    layout_kwargs = dict(
        uirevision="preserve",
        transition={"duration": 0},
        hovermode="closest",
        height=height,
        title_x=0.0,
        margin=dict(t=65, b=85 + extra_bottom_margin, l=60, r=40),
    )
    if xaxis_tickangle:
        layout_kwargs["xaxis_tickangle"] = xaxis_tickangle
    if legend_bottom:
        layout_kwargs["legend"] = dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        )
    fig.update_layout(**layout_kwargs)
    return fig
