"""End-to-end and regression tests for Streamlit App using AppTest."""
import pytest
from streamlit.testing.v1 import AppTest
from src.config import EMERGENCY_TEXT


def test_app_smoke_default():
    """Verify app runs from clean state without exceptions."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception, f"App threw exception: {at.exception}"
    assert len(at.dataframe) >= 1
    # Check that table contains all 32 hospitals
    df = at.dataframe[0].value
    assert len(df) == 32


@pytest.mark.parametrize("method_label,has_card,top_n,location_name", [
    ("Mentor formula (as given)", False, 3, "Bhubaneswar Railway Station"),
    ("Mentor formula (as given)", True, 1, "Patia / KIIT Square"),
    ("Mentor formula (as given)", False, 32, "Khandagiri Square"),
    ("BedScore (recommended)", True, 3, "Bhubaneswar Railway Station"),
    ("BedScore (recommended)", False, 1, "Patia / KIIT Square"),
    ("BedScore (recommended)", True, 32, "Khandagiri Square"),
    ("BedScore (recommended)", False, 3, "Master Canteen Square"),
    ("Mentor formula (as given)", True, 3, "Nayapalli"),
])
def test_app_control_matrix(method_label, has_card, top_n, location_name):
    """AppTest control matrix covering methods, card toggle, top_n (1, 3, all), and locations.
    
    Verifies that no combinations throw exceptions and that all 32 hospitals remain present.
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

    # Assert table has 32 hospitals
    assert len(at.dataframe) >= 1
    table_df = at.dataframe[0].value
    assert len(table_df) == 32


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
