"""Small normalization helpers shared across legacy compatibility code."""


def sanitize_annotation(name: str) -> str:
    """Enforce annotation naming rules: no dashes, brackets, or spaces."""
    name = name.replace("-", "_")
    name = name.replace("[", "(")
    name = name.replace("]", ")")
    name = name.replace(" ", "_")
    return name
