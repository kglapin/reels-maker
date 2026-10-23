"""Real-font typesetting with word geometry and balanced line breaking."""
from .typesetter import (
    FontBook, Line, Run, TextBlock, TextOverflow, TextStyle, Word,
    balanced_column, digits_width, fit_text, normalise_copy, typeset,
    typeset_runs,
)

__all__ = [
    "FontBook", "Line", "Run", "TextBlock", "TextOverflow", "TextStyle",
    "Word", "balanced_column", "digits_width", "fit_text", "normalise_copy",
    "typeset", "typeset_runs",
]
