"""Lookup helpers for autocomplete and selectors."""

from ..models import Feature, Organism, get_session


def get_feature_annotations(db_path: str) -> list[str]:
    """Return a sorted list of all feature annotation names."""
    session = get_session(db_path)
    try:
        rows = session.query(Feature.annotation).all()
        return sorted([row[0] for row in rows if row[0]])
    finally:
        session.close()


def get_organism_short_names(db_path: str) -> list[str]:
    """Return a sorted list of all organism short names."""
    session = get_session(db_path)
    try:
        rows = session.query(Organism.short_name).all()
        return sorted([row[0] for row in rows if row[0]])
    finally:
        session.close()
