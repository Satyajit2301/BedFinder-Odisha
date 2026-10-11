"""UI and HTML utilities for BedFinder Odisha."""
import html
import textwrap


def render_html(raw_html: str, **kwargs) -> str:
    """Safely format and clean HTML templates.
    
    1. Escapes dynamic string kwargs using html.escape to prevent injection.
    2. Dedents indentation.
    3. Strips empty lines between HTML tags.
    """
    escaped_kwargs = {
        k: html.escape(str(v)) if isinstance(v, str) else v
        for k, v in kwargs.items()
    }
    formatted = raw_html.format(**escaped_kwargs) if kwargs else raw_html
    dedented = textwrap.dedent(formatted).strip()
    cleaned = "\n".join(line for line in dedented.splitlines() if line.strip())
    return cleaned


def scheme_icon(val: str) -> str:
    """Return clean unicode icon for scheme acceptance."""
    s = str(val).lower().strip()
    if s in ("true", "yes", "1"):
        return "✓ Yes"
    elif s in ("false", "no", "0"):
        return "✗ No"
    return "? Confirm"


def status_word(p: float) -> tuple[str, str, str]:
    """Return (Word, ColourHex, Icon) for bed arrival probability."""
    if p >= 0.8:
        return "Likely", "#22AA5E", "🟢"
    elif p >= 0.5:
        return "Tight", "#FFAA00", "🟡"
    else:
        return "Unlikely", "#DC3545", "🔴"
