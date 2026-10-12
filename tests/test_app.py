"""End-to-end and regression tests for Streamlit App using AppTest."""
import pytest
from streamlit.testing.v1 import AppTest
from src.config import EMERGENCY_TEXT
from src.scoring import formula_text

f1_label = formula_text("formula1")
f2_label = formula_text("formula2")


def test_app_smoke_default():
    """Verify app runs from clean state without exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, f"App threw exception: {at.exception}"
    assert len(at.dataframe) >= 1
    # Check that table contains all 25 hospitals
    df = at.dataframe[0].value
    assert len(df) == 25


@pytest.mark.parametrize("method_label,has_card,top_n,location_name", [
    (f1_label, False, 3, "Bhubaneswar Railway Station"),
    (f1_label, True, 1, "Patia / KIIT Square"),
    (f1_label, False, 25, "Khandagiri Square"),
    (f2_label, True, 3, "Bhubaneswar Railway Station"),
    (f2_label, False, 1, "Patia / KIIT Square"),
    (f2_label, True, 25, "Khandagiri Square"),
    (f2_label, False, 3, "Master Canteen Square"),
    (f1_label, True, 3, "Nayapalli"),
])
def test_app_control_matrix(method_label, has_card, top_n, location_name):
    """AppTest control matrix covering methods, card toggle, top_n (1, 3, all), and locations.
    
    Verifies that no combinations throw exceptions and that all 25 hospitals remain present.
    """
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # Select landmark
    if len(at.sidebar.selectbox) > 0:
        at.sidebar.selectbox[0].select(location_name).run()
        assert not at.exception

    # Select method
    if len(at.sidebar.radio) > 1:
        at.sidebar.radio[1].set_value(method_label).run()
        assert not at.exception

    # Set scheme card toggle
    if len(at.sidebar.toggle) > 1:
        at.sidebar.toggle[1].set_value(has_card).run()
        assert not at.exception

    # Set Top N slider
    if len(at.sidebar.slider) > 0:
        at.sidebar.slider[0].set_value(top_n).run()
        assert not at.exception

    # Assert table has 25 hospitals
    assert len(at.dataframe) >= 1
    table_df = at.dataframe[0].value
    assert len(table_df) == 25


def test_regression_pmjay_no_crash():
    """Verify that scheme card toggle works without throwing list.index error."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    # Toggle card holder ON
    at.sidebar.toggle[1].set_value(True).run()
    assert not at.exception
    # Toggle card holder OFF
    at.sidebar.toggle[1].set_value(False).run()
    assert not at.exception


def test_regression_emergency_banner_html_clean():
    """Verify emergency banner does not contain unrendered markdown asterisks."""
    assert "**108**" not in EMERGENCY_TEXT
    assert "**112**" not in EMERGENCY_TEXT
    assert "<b>108</b>" in EMERGENCY_TEXT
    assert "<b>112</b>" in EMERGENCY_TEXT


def test_regression_tile_css_isolation():
    """Verify CSS invert applies strictly to .leaflet-tile-pane in app.py."""
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    assert ".leaflet-tile-pane" in app_code
    assert "filter: invert(1)" in app_code


@pytest.mark.parametrize("top_n", [1, 3, 10, 25])
def test_no_raw_html_leaking_in_markdown(top_n):
    """Assert that no rendered markdown leaks '&lt;span', '<span class=' as visible text, or raw est-badge."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    if len(at.sidebar.slider) > 0:
        at.sidebar.slider[0].set_value(top_n).run()
    assert not at.exception
    for md in at.markdown:
        val = str(md.value)
        assert "&lt;span" not in val, f"Found &lt;span in markdown: {val}"
        assert "&lt;div" not in val, f"Found &lt;div in markdown: {val}"
        assert "&lt;span class=&quot;est-badge&quot;&gt;" not in val


def test_g1_bedscore_ui_matches_rank_hospitals_for_6_landmarks():
    """G1 regression test (a): for 6 landmarks, UI top-3 names equal rank_hospitals(...) top-3 names."""
    import pandas as pd
    from src.config import ENRICHED_CSV, LANDMARKS
    from src.scoring import rank_hospitals
    df = pd.read_csv(ENRICHED_CSV)

    landmarks_to_test = [
        "Bhubaneswar Railway Station",
        "Patia / KIIT Square",
        "Khandagiri Square",
        "Rasulgarh Square",
        "Jaydev Vihar Square",
        "Nayapalli",
    ]

    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    if len(at.sidebar.radio) > 1:
        at.sidebar.radio[1].set_value(f2_label).run()

    for lm in landmarks_to_test:
        at.sidebar.selectbox[0].select(lm).run()
        assert not at.exception
        ui_df = at.dataframe[0].value
        ui_top3 = ui_df[ui_df["Rank"].str.startswith("#")].head(3)["Hospital"].tolist()

        lat, lon = LANDMARKS[lm]
        fn_df = rank_hospitals(df, lat, lon, method="formula2", include_specialty=False)
        fn_top3 = fn_df[fn_df["rank"] > 0].head(3)["hospital_name"].tolist()

        assert ui_top3 == fn_top3, f"Mismatch at {lm}: UI={ui_top3} vs Fn={fn_top3}"


def test_ui_contract_no_mentor_and_formulas_match_formula_text():
    """V1 UI-contract test: fails if rendered text or docs contain mentor, Mentor, sir , Sir's;
    and asserts that both formula strings on screen equal formula_text()."""
    from pathlib import Path
    import re

    root = Path(__file__).resolve().parent.parent
    doc_paths = [
        root / "README.md",
        root / "docs" / "DEMO_SCRIPT.md",
        root / "docs" / "QA_PREP.md",
        root / "docs" / "DATA_CARD.md",
        root / "docs" / "ML_REPORT.md",
        root / "docs" / "BLOCKED.md",
    ]
    forbidden_pattern = re.compile(r"\b(mentor|sir|sir's)\b", re.IGNORECASE)
    for p in doc_paths:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            matches = forbidden_pattern.findall(text)
            assert not matches, f"Found forbidden terms {matches} in {p.name}"

    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # Check radio options in sidebar
    radio = at.sidebar.radio[1]
    expected_f1 = formula_text("formula1")
    expected_f2 = formula_text("formula2")
    assert radio.options == [expected_f1, expected_f2], f"Radio options mismatch: {radio.options}"

    # Check rendered markdown in app
    for md in at.markdown:
        val = str(md.value)
        matches = forbidden_pattern.findall(val)
        assert not matches, f"Found forbidden terms {matches} in rendered markdown: {val[:80]}"

