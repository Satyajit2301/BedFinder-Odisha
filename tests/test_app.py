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
    if len(at.sidebar.radio) > 0:
        at.sidebar.radio[0].set_value(method_label).run()
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
    card_toggle_on = [t for t in at.sidebar.toggle if "card" in t.label.lower()][0]
    # Toggle card holder ON
    card_toggle_on.set_value(True).run()
    assert not at.exception
    # Toggle card holder OFF (re-query node from new tree)
    card_toggle_off = [t for t in at.sidebar.toggle if "card" in t.label.lower()][0]
    card_toggle_off.set_value(False).run()
    assert not at.exception




def test_regression_emergency_banner_html_clean():
    """Verify emergency banner does not contain unrendered markdown asterisks."""
    assert "**108**" not in EMERGENCY_TEXT
    assert "**112**" not in EMERGENCY_TEXT
    assert "<b>108</b>" in EMERGENCY_TEXT
    assert "<b>112</b>" in EMERGENCY_TEXT


def test_regression_tile_css_isolation():
    """Verify CartoDB dark-matter tiles are used and leaflet CSS invert filter is removed per V7."""
    with open("app.py", "r", encoding="utf-8") as f:
        app_code = f.read()
    assert "cartocdn.com/dark_all" in app_code
    assert "filter: invert(1)" not in app_code



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
    if len(at.sidebar.radio) > 0:
        at.sidebar.radio[0].set_value(f2_label).run()

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
    radio = at.sidebar.radio[0]
    expected_f1 = formula_text("formula1")
    expected_f2 = formula_text("formula2")
    assert radio.options == [expected_f1, expected_f2], f"Radio options mismatch: {radio.options}"

    # Check rendered markdown in app
    for md in at.markdown:
        val = str(md.value)
        matches = forbidden_pattern.findall(val)
        assert not matches, f"Found forbidden terms {matches} in rendered markdown: {val[:80]}"


def test_v3_sort_table_by():
    """V3 requirement: row count unchanged for every sort, Rank values unchanged, Cheapest uses effective fee."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # Default sort
    df_default = at.dataframe[0].value
    assert len(df_default) == 25
    rank_mapping = dict(zip(df_default["Hospital"], df_default["Rank"]))

    sort_options = [
        "Recommended rank",
        "Nearest",
        "Cheapest (effective fee)",
        "Highest rated",
        "Most beds free",
    ]

    # Find the sort selectbox
    sort_sb_list = [s for s in at.selectbox if s.key == "sort_table_by"]
    assert len(sort_sb_list) == 1, "sort_table_by selectbox not found"
    sort_sb = sort_sb_list[0]

    for opt in sort_options:
        sort_sb.select(opt).run()
        assert not at.exception
        df_sorted = at.dataframe[0].value
        # Row count unchanged
        assert len(df_sorted) == 25, f"Row count changed for sort: {opt}"
        # Rank column values unchanged for each hospital
        for _, row in df_sorted.iterrows():
            hosp = row["Hospital"]
            assert row["Rank"] == rank_mapping[hosp], f"Rank value changed for {hosp} in sort {opt}"

    # Test "Cheapest" with scheme card ON: cashless rows (fee 0) must appear first
    card_toggle = [t for t in at.sidebar.toggle if "card" in t.label.lower()][0]
    card_toggle.set_value(True).run()
    assert not at.exception
    sort_sb = [s for s in at.selectbox if s.key == "sort_table_by"][0]
    sort_sb.select("Cheapest (effective fee)").run()
    assert not at.exception
    df_card_cheap = at.dataframe[0].value
    first_hosp = df_card_cheap.iloc[0]
    # Top rows must accept cashless scheme (PM-JAY or GJAY or Scheme column) or have Rs 0 fee
    assert "✓" in str(first_hosp.get("Scheme", "")) or "✓" in str(first_hosp.get("PM-JAY", "")) or "Rs 0" in str(first_hosp["Fee/day"]) or first_hosp["Fee/day"] == 0


def test_v5_ui_card_effects():
    """V5: with card ON, displayed fee contains Rs 0 for flagged rows, cashless badge, and rank arrows."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    # Toggle card ON
    card_toggle = [t for t in at.sidebar.toggle if "card" in t.label.lower()][0]
    card_toggle.set_value(True).run()
    assert not at.exception
    df = at.dataframe[0].value
    # Find flagged hospital (Scheme == ✓)
    flagged_rows = df[df["Scheme"] == "✓"]
    assert len(flagged_rows) == 12, f"Expected 12 flagged hospitals in table, got {len(flagged_rows)}"
    first_flagged = flagged_rows.iloc[0]
    assert "Rs 0" in str(first_flagged["Fee/day"])
    # Check that rank arrows ▲ or ▼ appear in table for hospitals that changed rank
    has_arrow = any("▲" in str(r) or "▼" in str(r) for r in df["Rank"])
    assert has_arrow, "Expected rank arrows (▲/▼) in Rank column when card is ON"


def test_v6_demo_tools_and_simulation():
    """V6: simulation banner appears when active; reset restores snapshot; 0 beds at Apollo triggers Full, flagged, placed after unflagged; row count unchanged."""
    at = AppTest.from_file("app.py", default_timeout=30)
    # Start with active simulation of 0 beds for Apollo
    at.session_state["sim_hosp"] = "Apollo Hospitals Bhubaneswar"
    at.session_state["sim_beds"] = 0
    at.run()
    assert not at.exception

    # 1. Coloured banner appears at the TOP of results
    banner_found = any("SIMULATION ACTIVE: Apollo Hospitals Bhubaneswar set to 0 free beds" in str(md.value) for md in at.markdown)
    assert banner_found, "Simulation banner not found when simulation is active"

    # 2. Table row count strictly remains 25
    df = at.dataframe[0].value
    assert len(df) == 25, f"Row count changed during simulation: {len(df)}"

    # 3. Apollo status is 'Likely full' and placed after unflagged hospitals
    apollo_row = df[df["Hospital"].str.contains("Apollo")].iloc[0]
    assert "Likely full" in str(apollo_row["Bed status (ML)"])
    apollo_rank = int(str(apollo_row["Rank"]).replace("#", "").split()[0])
    unflagged_rows = df[~df["Hospital"].str.contains("Apollo")]
    ranked_unflagged = [int(str(r).replace("#", "").split()[0]) for r in unflagged_rows["Rank"] if str(r).startswith("#")]
    assert apollo_rank > max(ranked_unflagged), "Flagged Apollo must be placed after all unflagged ranked hospitals"

    # 4. Reset restores snapshot exactly
    reset_btn = [b for b in at.button if b.key == "btn_reset_simulation"][0]
    reset_btn.click().run()
    assert not at.exception
    # After reset, banner is gone and Apollo beds restored
    df_reset = at.dataframe[0].value
    apollo_reset = df_reset[df_reset["Hospital"].str.contains("Apollo")].iloc[0]
    assert "22" in str(apollo_reset["Beds free"])
    assert not any("SIMULATION ACTIVE:" in str(md.value) for md in at.markdown)



def test_v6_demo_tools_hidden_when_demo_mode_false(monkeypatch):
    """V6: Whole demo tools panel is hidden when DEMO_MODE is False."""
    import src.config
    monkeypatch.setattr(src.config, "DEMO_MODE", False)
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception
    demo_tools_expanders = [e for e in at.expander if "Demo tools" in str(e.label)]
    assert len(demo_tools_expanders) == 0, "Demo tools expander must be hidden when DEMO_MODE is False"


def test_v9_smart_search_controls_flow():
    """V9: Smart search extracts place, card, and sort, updating widgets and allowing Undo."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # Apply search query
    search_input = [t for t in at.text_input if t.key == "smart_search_input"][0]
    search_input.input("near Patia, I have an Ayushman card, cheapest first").run()
    apply_btn = [b for b in at.button if b.key == "btn_smart_search_apply"][0]
    apply_btn.click().run()
    assert not at.exception

    # Assert controls updated
    loc = at.session_state["loc"]
    assert "Patia" in loc["label"]
    assert at.session_state["user_has_card_toggle"] is True
    assert at.session_state["sort_table_by"] == "Cheapest (effective fee)"

    # Assert understood feedback message displayed
    understood_found = any("I understood:" in str(info.value) for info in at.info)
    assert understood_found

    # Test Undo button
    undo_btn = [b for b in at.button if b.key == "btn_smart_search_undo"][0]
    undo_btn.click().run()
    assert not at.exception
    assert at.session_state["user_has_card_toggle"] is False


def test_v9_smart_search_emergency_banner():
    """V9: Emergency keywords in smart search trigger immediate 108/112 alert."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    search_input = [t for t in at.text_input if t.key == "smart_search_input"][0]
    search_input.input("severe chest pain and bleeding from accident").run()
    apply_btn = [b for b in at.button if b.key == "btn_smart_search_apply"][0]
    apply_btn.click().run()
    assert not at.exception

    emergency_alert_found = any("MEDICAL EMERGENCY DETECTED" in str(err.value) for err in at.error)
    assert emergency_alert_found



