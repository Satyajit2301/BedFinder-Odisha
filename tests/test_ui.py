"""Unit tests for UI utilities and front-end helpers."""
import pytest
from src.ui_utils import render_html, scheme_icon, status_word
from src.config import ODISHA_BOUNDS, EMERGENCY_TEXT


def test_render_html_escapes_xss():
    template = "<div>{content}</div>"
    raw_input = "<script>alert('xss')</script>"
    result = render_html(template, content=raw_input)
    assert "<script>" not in result
    assert "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in result
    assert result.startswith("<div>")


def test_render_html_dedents_and_cleans():
    template = """
        <div class="card">
            <p>Hello World</p>
        </div>
    """
    result = render_html(template)
    lines = result.splitlines()
    assert lines[0] == '<div class="card">'
    assert lines[1] == '    <p>Hello World</p>'
    assert lines[2] == '</div>'
    assert len(lines) == 3


def test_status_word_thresholds():
    word_high, col_high, ico_high = status_word(0.95)
    assert word_high == "Likely"
    assert ico_high == "🟢"

    word_mid, col_mid, ico_mid = status_word(0.65)
    assert word_mid == "Tight"
    assert ico_mid == "🟡"

    word_low, col_low, ico_low = status_word(0.30)
    assert word_low == "Unlikely"
    assert ico_low == "🔴"


def test_scheme_icon():
    assert scheme_icon("true") == "✓ Yes"
    assert scheme_icon("false") == "✗ No"
    assert scheme_icon("unknown") == "? Confirm"


def test_emergency_text_contains_clean_html():
    assert "<b>108</b>" in EMERGENCY_TEXT
    assert "<b>112</b>" in EMERGENCY_TEXT
    assert "**108**" not in EMERGENCY_TEXT
    assert "**112**" not in EMERGENCY_TEXT


def test_odisha_bounds():
    # Valid Bhubaneswar coordinate
    bb_lat, bb_lon = 20.2961, 85.8245
    assert ODISHA_BOUNDS["lat_min"] <= bb_lat <= ODISHA_BOUNDS["lat_max"]
    assert ODISHA_BOUNDS["lon_min"] <= bb_lon <= ODISHA_BOUNDS["lon_max"]

    # Invalid Delhi coordinate
    delhi_lat, delhi_lon = 28.6139, 77.2090
    assert not (ODISHA_BOUNDS["lat_min"] <= delhi_lat <= ODISHA_BOUNDS["lat_max"])
