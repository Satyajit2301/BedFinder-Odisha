"""UI and HTML utilities for BedFinder Odisha."""
import html
import textwrap


class SafeHTML(str):
    """Marker for trusted HTML strings that should not be re-escaped."""
    pass


def safe_html(text: str) -> SafeHTML:
    """Wrap trusted HTML string so render_html does not re-escape it."""
    return SafeHTML(text)


def render_html(raw_html: str, **kwargs) -> str:
    """Safely format and clean HTML templates.
    
    1. Escapes dynamic string kwargs using html.escape to prevent injection,
       unless marked as SafeHTML.
    2. Dedents indentation.
    3. Strips empty lines between HTML tags.
    """
    escaped_kwargs = {
        k: v if isinstance(v, SafeHTML) else (html.escape(str(v)) if isinstance(v, str) else v)
        for k, v in kwargs.items()
    }
    formatted = raw_html.format(**escaped_kwargs) if kwargs else raw_html
    dedented = textwrap.dedent(formatted).strip()
    cleaned = "\n".join(line for line in dedented.splitlines() if line.strip())
    return cleaned


def scheme_icon(val: str, is_html: bool = False) -> str:
    """Return clean unicode icon for scheme acceptance."""
    s = str(val).lower().strip()
    if s in ("true", "yes", "1"):
        return safe_html('<span title="demo">✓ Yes</span>') if is_html else "✓ Yes"
    elif s in ("false", "no", "0"):
        return safe_html('<span title="demo">✗ No</span>') if is_html else "✗ No"
    return safe_html('<span title="demo">? Confirm</span>') if is_html else "? Confirm"


def status_word(p: float) -> tuple[str, str, str]:
    """Return (Word, ColourHex, Icon) for bed arrival probability."""
    if p >= 0.8:
        return "Likely", "#22AA5E", "🟢"
    elif p >= 0.5:
        return "Tight", "#FFAA00", "🟡"
    else:
        return "Unlikely", "#DC3545", "🔴"


def format_p(p: float) -> str:
    """Format bed arrival probability P per UI requirement V7:
    - one decimal ("99.6%")
    - show "≥99.9%" instead of "100%" unless it is exactly 1.0
    - show "<0.1%" if non-zero but below 0.001
    """
    if p >= 1.0:
        return "100%"
    if p >= 0.999:
        return "≥99.9%"
    if p <= 0.001 and p > 0.0:
        return "<0.1%"
    return f"{p * 100:.1f}%"

