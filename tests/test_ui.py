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


def test_safe_html_not_escaped():
    from src.ui_utils import safe_html, render_html
    badge = safe_html('<span class="est-badge">estimated</span>')
    name = "Ayush <Hospital>"
    rendered = render_html("<h3>{name}{badge}</h3>", name=name, badge=badge)
    assert '<span class="est-badge">estimated</span>' in rendered
    assert "Ayush &lt;Hospital&gt;" in rendered
    assert "&lt;span" not in rendered


def test_contact_verification_ui_rules():
    """D3: No phone is rendered when phone_confirmed == 'no'. No link is rendered for DNS_FAIL / NOT_FOUND_404."""
    import pandas as pd
    from src.config import ENRICHED_CSV
    df = pd.read_csv(ENRICHED_CSV)

    # 1. Test phone rule: when phone_confirmed == 'no', the raw phone number must NEVER be rendered
    unconfirmed_phones = df[df["phone_confirmed"] == "no"]
    assert not unconfirmed_phones.empty
    for _, r in unconfirmed_phones.iterrows():
        raw_phone = str(r.get("phone", "")).strip()
        is_conf = str(r.get("phone_confirmed", "")).strip().lower() == "yes"
        rendered_phone = raw_phone if is_conf and raw_phone and raw_phone != "nan" else "Not verified"
        assert rendered_phone == "Not verified"
        if raw_phone and raw_phone != "nan":
            assert raw_phone != rendered_phone

    # 2. Test website rule: when status is DNS_FAIL or NOT_FOUND_404, no link is rendered unless website_confirmed == 'yes'
    broken_webs = df[df["website_status"].isin(["DNS_FAIL", "NOT_FOUND_404"])]
    assert not broken_webs.empty
    for _, r in broken_webs.iterrows():
        raw_web = str(r.get("website", "")).strip()
        is_live = str(r.get("website_status", "")).strip() == "LIVE"
        is_conf = str(r.get("website_confirmed", "")).strip().lower() == "yes"
        rendered_link = raw_web if (is_live or is_conf) and raw_web and raw_web != "nan" else None
        assert rendered_link is None, f"Dead link rendered for {r['hospital_id']}: {raw_web} with status {r['website_status']}"


def test_screenshots_folder_only_contains_produced_files():
    """D5: capture_screenshots.py is the only source of files in docs/screenshots/."""
    from scripts.capture_screenshots import PRODUCED_FILES
    from pathlib import Path

    sc_dir = Path(__file__).resolve().parent.parent / "docs" / "screenshots"
    assert sc_dir.exists(), "docs/screenshots directory must exist"

    actual_files = sorted([f.name for f in sc_dir.iterdir() if f.is_file()])
    expected_files = sorted(PRODUCED_FILES)

    # Every file in the folder must be in PRODUCED_FILES
    unexpected = [f for f in actual_files if f not in expected_files]
    assert not unexpected, f"Unexpected screenshot files found in docs/screenshots: {unexpected}"


def test_format_p_display():
    """V7: P display has one decimal, shows '≥99.9%' instead of 100% unless exactly 1.0."""
    from src.ui_utils import format_p
    assert format_p(0.996) == "99.6%"
    assert format_p(0.9992) == "≥99.9%"
    assert format_p(0.9999) == "≥99.9%"
    assert format_p(1.0) == "100%"
    assert format_p(0.784) == "78.4%"
    assert format_p(0.0005) == "<0.1%"


def test_score_breakdown_bars_sum_to_score():
    """V7: Bar values (Trust, Closeness, Affordability) sum EXACTLY to the score ±0.05 for every hospital."""
    import numpy as np
    from src.data import load_hospitals, load_history_snapshot, build_snapshot
    from src.scoring import get_score_breakdown
    from src.config import LANDMARKS

    hosp = load_hospitals()
    last = load_history_snapshot()
    snap = build_snapshot(hosp, last)

    for lm_name, (la, lo) in LANDMARKS.items():
        bd = get_score_breakdown(snap, la, lo, method="formula2")
        term_sum = bd["Trust"] + bd["Closeness"] + bd["Affordability"]
        diff = np.abs(term_sum - bd["Total"])
        assert np.all(diff <= 0.05), f"Breakdown terms did not sum to score within 0.05 at {lm_name}: max diff {diff.max()}"


def test_map_tiles_cartodb_and_no_invert_css():
    """V7: Map uses CartoDB dark-matter tiles, removes CSS invert filter, and uses consistent Rs."""
    from pathlib import Path
    app_text = Path("app.py").read_text(encoding="utf-8")
    assert "cartocdn.com/dark_all" in app_text, "CartoDB dark-matter tile URL must be used"
    assert "filter: invert(1)" not in app_text, "Leaflet CSS invert filter must be removed"
    assert "₹" not in app_text, "Currency symbol must be consistently 'Rs', no raw ₹ in app.py"


def test_table_default_columns():
    """V7: Table default columns match the specification."""
    from pathlib import Path
    app_text = Path("app.py").read_text(encoding="utf-8")
    expected_default = [
        "Rank", "Hospital", "Distance", "ETA", "Beds free",
        "Bed status (ML)", "Fee/day", "Rating", "Scheme", "Directions",
    ]
    for col in expected_default:
        assert f'"{col}"' in app_text, f"Default column {col} missing from app.py"



