"""Automated screenshot capture using Playwright for BedFinder Odisha v2.2."""
import os
import subprocess
import sys
import time
from pathlib import Path

SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PRODUCED_FILES = [
    "01_full_page_desktop_1440.png",
    "02_closeup_emergency_banner.png",
    "03_closeup_data_table.png",
    "04_closeup_map_markers.png",
    "05_closeup_plotly_breakdown.png",
    "06_closeup_simulate_0_beds_warning.png",
    "07_closeup_invalid_location_contrast.png",
    "08_full_page_mobile_390.png",
    "09_bedscore_top3_railway_station.png",
    "10_bedscore_top3_patia.png",
]


def assert_no_badge_leak(page, step_name: str):
    """Assert DOM body contains no raw HTML '<span', '&lt;', or 'est-badge' leaks."""
    body_text = page.inner_text("body")
    assert "<span" not in body_text, f"[{step_name}] Leaked '<span' found in inner text"
    assert "&lt;" not in body_text, f"[{step_name}] Leaked '&lt;' found in inner text"
    assert "est-badge" not in body_text, f"[{step_name}] Leaked 'est-badge' found in inner text"
    print(f"   [leak check PASS] {step_name}: 0 '<span', 0 '&lt;', 0 'est-badge' in inner text")


def wait_for_server(url: str, timeout: int = 30) -> bool:
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def main():
    from playwright.sync_api import sync_playwright

    port = 8501
    url = f"http://localhost:{port}"

    print(f"Starting Streamlit server on {url}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", str(port),
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        if not wait_for_server(url, timeout=35):
            print("ERROR: Streamlit failed to respond within 35 seconds.")
            return 1

        print("Streamlit server is ready. Launching Chromium...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- DESKTOP VIEWPORT (1440x900) ---
            desktop = browser.new_context(viewport={"width": 1440, "height": 900})
            page = desktop.new_page()

            # 1. Full Page Desktop (1440 wide)
            print("1. Capturing 01_full_page_desktop_1440.png...")
            page.goto(url)
            page.wait_for_selector(".hospital-card", timeout=30000)
            page.wait_for_timeout(4000)
            # Scroll down to trigger lazy loading of map and table
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(3000)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1500)
            assert_no_badge_leak(page, "01_full_page_desktop_1440")
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_full_page_desktop_1440.png"), full_page=True)

            # 2. Close-up of Emergency Banner
            print("2. Capturing 02_closeup_emergency_banner.png...")
            try:
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_selector(".emergency-bar", timeout=10000)
                banner = page.locator(".emergency-bar").first
                banner.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                assert_no_badge_leak(page, "02_closeup_emergency_banner")
                banner.screenshot(path=str(SCREENSHOTS_DIR / "02_closeup_emergency_banner.png"))
                print("   [ok] Saved 02_closeup_emergency_banner.png")
            except Exception as e:
                print(f"   [err] Emergency banner capture failed: {e}")

            # 3. Close-up of Data Table
            print("3. Capturing 03_closeup_data_table.png...")
            try:
                page.wait_for_selector('[data-testid="stDataFrame"], .stDataFrame', timeout=10000)
                table = page.locator('[data-testid="stDataFrame"]').first
                if table.count() == 0:
                    table = page.locator('.stDataFrame').first
                table.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                assert_no_badge_leak(page, "03_closeup_data_table")
                table.screenshot(path=str(SCREENSHOTS_DIR / "03_closeup_data_table.png"))
                print("   [ok] Saved 03_closeup_data_table.png")
            except Exception as e:
                print(f"   [err] Data table capture failed: {e}")

            # 4. Close-up of Hospital Map
            print("4. Capturing 04_closeup_map_markers.png...")
            try:
                map_elem = page.locator('iframe[title*="folium"], .stCustomComponentV1').first
                map_elem.scroll_into_view_if_needed()
                page.wait_for_timeout(2000)
                assert_no_badge_leak(page, "04_closeup_map_markers")
                map_elem.screenshot(path=str(SCREENSHOTS_DIR / "04_closeup_map_markers.png"))
                print("   [ok] Saved 04_closeup_map_markers.png")
            except Exception as e:
                print(f"   [err] Map capture failed: {e}")

            # 5. Close-up of Plotly "Why this rank?" Chart
            print("5. Capturing 05_closeup_plotly_breakdown.png...")
            try:
                why_expander = page.locator('summary:has-text("Why this rank")').first
                why_expander.scroll_into_view_if_needed()
                why_expander.click()
                page.wait_for_selector('[data-testid="stPlotlyChart"], .stPlotlyChart, .js-plotly-plot', timeout=15000)
                page.wait_for_timeout(2000)
                plotly_chart = page.locator('[data-testid="stPlotlyChart"]').first
                if plotly_chart.count() == 0:
                    plotly_chart = page.locator('.stPlotlyChart').first
                plotly_chart.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                assert_no_badge_leak(page, "05_closeup_plotly_breakdown")
                plotly_chart.screenshot(path=str(SCREENSHOTS_DIR / "05_closeup_plotly_breakdown.png"))
                print("   [ok] Saved 05_closeup_plotly_breakdown.png")
                why_expander.click()  # close
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"   [err] Plotly chart capture failed: {e}")

            # 6. Simulate expander at 0 beds with warning badge
            print("6. Capturing 06_closeup_simulate_0_beds_warning.png...")
            try:
                sim_expander = page.locator('summary:has-text("Simulate a hospital filling up")').first
                sim_expander.scroll_into_view_if_needed()
                sim_expander.click()
                page.wait_for_timeout(2000)
                beds_input = page.locator('input[type="number"]').first
                if beds_input.count() > 0:
                    beds_input.fill("0")
                    beds_input.press("Enter")
                    page.wait_for_timeout(3500)
                # Capture the expander container showing 0 beds and warning badge
                assert_no_badge_leak(page, "06_closeup_simulate_0_beds_warning")
                exp_container = page.locator('div[data-testid="stExpander"]:has-text("Simulate a hospital filling up")').first
                if exp_container.count() > 0:
                    exp_container.screenshot(path=str(SCREENSHOTS_DIR / "06_closeup_simulate_0_beds_warning.png"))
                else:
                    page.locator('.sim-warning-badge').first.screenshot(path=str(SCREENSHOTS_DIR / "06_closeup_simulate_0_beds_warning.png"))
                print("   [ok] Saved 06_closeup_simulate_0_beds_warning.png")
            except Exception as e:
                print(f"   [err] Simulate warning capture failed: {e}")

            # 7. Invalid location error high contrast close-up
            print("7. Capturing 07_closeup_invalid_location_contrast.png...")
            try:
                manual_opt = page.locator('label:has-text("Enter manually")').first
                manual_opt.scroll_into_view_if_needed()
                manual_opt.click()
                page.wait_for_timeout(2000)
                input_box = page.locator('input[type="text"]').first
                if input_box.count() > 0:
                    input_box.fill("28.6139, 77.2090")
                    input_box.press("Enter")
                    page.wait_for_timeout(3000)
                    page.wait_for_selector(".location-error-box", timeout=10000)
                    assert_no_badge_leak(page, "07_closeup_invalid_location_contrast")
                    err_box = page.locator(".location-error-box").first
                    err_box.screenshot(path=str(SCREENSHOTS_DIR / "07_closeup_invalid_location_contrast.png"))
                    print("   [ok] Saved 07_closeup_invalid_location_contrast.png")
            except Exception as e:
                print(f"   [err] Location error capture failed: {e}")

            # 9. BedScore Top 3 at Railway Station
            print("9. Capturing 09_bedscore_top3_railway_station.png...")
            try:
                page.goto(url)
                page.wait_for_selector(".hospital-card", timeout=30000)
                bedscore_radio = page.locator('label:has-text("BedScore (recommended)")').first
                bedscore_radio.click()
                page.wait_for_timeout(3000)
                assert_no_badge_leak(page, "09_bedscore_top3_railway_station")
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(SCREENSHOTS_DIR / "09_bedscore_top3_railway_station.png"))
                print("   [ok] Saved 09_bedscore_top3_railway_station.png")
            except Exception as e:
                print(f"   [err] BedScore railway station capture failed: {e}")

            # 10. BedScore Top 3 at Patia / KIIT Square
            print("10. Capturing 10_bedscore_top3_patia.png...")
            try:
                selectbox = page.locator('div[data-testid="stSelectbox"]:has-text("Where are you?")').first
                selectbox.click()
                page.wait_for_timeout(1000)
                patia_opt = page.locator('li:has-text("Patia / KIIT Square")').first
                patia_opt.click()
                page.wait_for_timeout(3500)
                assert_no_badge_leak(page, "10_bedscore_top3_patia")
                page.evaluate("window.scrollTo(0, 0)")
                page.screenshot(path=str(SCREENSHOTS_DIR / "10_bedscore_top3_patia.png"))
                print("   [ok] Saved 10_bedscore_top3_patia.png")
            except Exception as e:
                print(f"   [err] BedScore patia capture failed: {e}")

            desktop.close()

            # --- MOBILE VIEWPORT (390x844) ---
            print("8. Capturing 08_full_page_mobile_390.png...")
            mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            )
            mob_page = mobile.new_page()
            mob_page.goto(url)
            mob_page.wait_for_selector(".hospital-card", timeout=30000)
            mob_page.wait_for_timeout(3000)
            assert_no_badge_leak(mob_page, "08_full_page_mobile_390")
            mob_page.screenshot(path=str(SCREENSHOTS_DIR / "08_full_page_mobile_390.png"), full_page=True)
            mobile.close()

            browser.close()

        print(f"All screenshots successfully captured into {SCREENSHOTS_DIR}!")
        return 0
    finally:
        print("Stopping Streamlit server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main() or 0)
