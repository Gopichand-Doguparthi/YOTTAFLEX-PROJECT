"""
Shared lookup helpers for dashboard views.
Provides ID-to-name resolution for Role, Level, and Location.
Cached per session to avoid repeated DB queries.
"""
from sqlalchemy.orm import Session


def get_role_map(db: Session) -> dict:
    """Returns {role_id: role_title}"""
    from src.database.models import Role
    return {r.role_id: r.role_title for r in db.query(Role).all()}


def get_level_map(db: Session) -> dict:
    """Returns {level_id: 'Level Name (Code)'}"""
    from src.database.models import Level
    return {l.level_id: f"{l.level_name} ({l.level_code})" for l in db.query(Level).all()}


def get_location_map(db: Session) -> dict:
    """Returns {location_id: location_name}"""
    from src.database.models import Location
    return {loc.location_id: loc.location_name for loc in db.query(Location).all()}


def resolve(id_val: str, lookup: dict) -> str:
    """Resolve an ID to its name, returning original if not found."""
    return lookup.get(id_val, id_val)


def map_col(df, col: str, lookup: dict, new_col: str = None):
    """Map a DataFrame column of IDs to human names in-place."""
    target = new_col or col
    df[target] = df[col].map(lambda x: lookup.get(x, x))
    return df


PLOTLY_CONFIG = {"scrollZoom": True, "displayModeBar": True}
