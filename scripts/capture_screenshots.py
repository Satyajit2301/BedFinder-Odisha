"""Automated screenshot capture using Playwright for BedFinder Odisha.

Captures all 11 required visual artifacts:
01_default_view_desktop_1440.png
02_formula2_railway_station.png
03_formula2_khandagiri.png
04_formula1_view.png
05_card_on_scheme_effects.png
06_ml_forecast_and_accuracy.png
07_demo_tools_flagged_hospital.png
08_smart_search_result_line.png
09_gps_location_chip.png
10_table_desktop_1440_no_scroll.png
11_full_page_mobile_390.png
"""
import os
import subprocess
import sys
import time
from pathlib import Path

SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PRODUCED_FILES = [
    "01_default_view_desktop_1440.png",
    "02_formula2_railway_station.png",
    "03_formula2_khandagiri.png",
    "04_formula1_view.png",
    "05_card_on_scheme_effects.png",
    "06_ml_forecast_and_accuracy.png",
    "07_demo_tools_flagged_hospital.png",
    "08_smart_search_result_line.png",
    "09_gps_location_chip.png",
    "10_table_desktop_1440_no_scroll.png",
    "11_full_page_mobile_390.png",
]


def assert_no_badge_leak(page, step_name: str):
    """Assert DOM body contains no raw HTML '<span', '&lt;', or 'est-badge' leaks."""
    body_text = page.inner_text("body")
    assert "<span" not in body_text, f"[{step_name}] Leaked '<span' found in inner text"
    assert "&lt;" not in body_text, f"[{step_name}] Leaked '&lt;' found in inner text"
    assert "est-badge" not in body_text, f"[{step_name}] Leaked 'est-badge' found in inner text"
    print(f"   [leak check PASS] {step_name}: 0 '<span', 0 '&lt;', 0 'est-badge' in inner text")


def wait_for_server(url: str, timeout: int = 35) -> bool:
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

    # Clean existing screenshots to ensure only PRODUCED_FILES remain
    for f in SCREENSHOTS_DIR.iterdir():
        if f.is_file():
            try:
                f.unlink()
            except Exception:
                pass

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
        if not wait_for_server(url, timeout=40):
            print("ERROR: Streamlit failed to respond within timeout.")
            return 1

        print("Streamlit server is ready. Launching Chromium...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # --- DESKTOP VIEWPORT (1440x900) ---
            desktop = browser.new_context(viewport={"width": 1440, "height": 900})
            page = desktop.new_page()
            page.set_default_timeout(10000)

            # 1. Default View Desktop (1440)
            print("1. Capturing 01_default_view_desktop_1440.png...")
            page.goto(url)
            page.wait_for_selector(".hospital-card", timeout=25000)
            page.wait_for_timeout(2500)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(1000)
            assert_no_badge_leak(page, "01_default_view_desktop_1440")
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_default_view_desktop_1440.png"), full_page=True)
            print("   [ok] Saved 01_default_view_desktop_1440.png")

            # 2. Formula 2 at Railway Station
            print("2. Capturing 02_formula2_railway_station.png...")
            try:
                sb = page.locator('section[data-testid="stSidebar"] div[data-baseweb="select"]').first
                sb.click()
                page.keyboard.type("Bhubaneswar Railway Station")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 0)")
                assert_no_badge_leak(page, "02_formula2_railway_station")
                page.screenshot(path=str(SCREENSHOTS_DIR / "02_formula2_railway_station.png"))
                print("   [ok] Saved 02_formula2_railway_station.png")
            except Exception as e:
                print(f"   [err] Railway station capture failed: {e}")

            # 3. Formula 2 at Khandagiri Square
            print("3. Capturing 03_formula2_khandagiri.png...")
            try:
                sb = page.locator('section[data-testid="stSidebar"] div[data-baseweb="select"]').first
                sb.click()
                page.keyboard.type("Khandagiri Square")
                page.keyboard.press("Enter")
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 0)")
                assert_no_badge_leak(page, "03_formula2_khandagiri")
                page.screenshot(path=str(SCREENSHOTS_DIR / "03_formula2_khandagiri.png"))
                print("   [ok] Saved 03_formula2_khandagiri.png")
            except Exception as e:
                print(f"   [err] Khandagiri capture failed: {e}")

            # 4. Formula 1 View
            print("4. Capturing 04_formula1_view.png...")
            try:
                f1_radio = page.locator('label:has-text("Formula 1")').first
                f1_radio.click()
                page.wait_for_timeout(2000)
                page.evaluate("window.scrollTo(0, 0)")
                assert_no_badge_leak(page, "04_formula1_view")
                page.screenshot(path=str(SCREENSHOTS_DIR / "04_formula1_view.png"))
                print("   [ok] Saved 04_formula1_view.png")
                # Switch back to Formula 2
                page.locator('label:has-text("Formula 2")').first.click()
                page.wait_for_timeout(1500)
            except Exception as e:
                print(f"   [err] Formula 1 capture failed: {e}")

            # 5. Card ON Scheme Effects
            print("5. Capturing 05_card_on_scheme_effects.png...")
            try:
                card_toggle = page.locator('section[data-testid="stSidebar"] label:has-text("Ayushman")').first
                card_toggle.click()
                page.wait_for_timeout(2500)
                page.evaluate("window.scrollTo(0, 0)")
                assert_no_badge_leak(page, "05_card_on_scheme_effects")
                page.screenshot(path=str(SCREENSHOTS_DIR / "05_card_on_scheme_effects.png"))
                print("   [ok] Saved 05_card_on_scheme_effects.png")
            except Exception as e:
                print(f"   [err] Card ON capture failed: {e}")

            # 6. ML Forecast and Accuracy Panel
            print("6. Capturing 06_ml_forecast_and_accuracy.png...")
            try:
                page.evaluate("window.scrollTo(0, 1100)")
                page.wait_for_timeout(1000)
                exp = page.locator('summary:has-text("How good is the ML model")').first
                if exp.count() > 0:
                    exp.scroll_into_view_if_needed()
                    exp.click()
                    page.wait_for_timeout(1500)
                assert_no_badge_leak(page, "06_ml_forecast_and_accuracy")
                page.screenshot(path=str(SCREENSHOTS_DIR / "06_ml_forecast_and_accuracy.png"))
                print("   [ok] Saved 06_ml_forecast_and_accuracy.png")
            except Exception as e:
                print(f"   [err] ML forecast capture failed: {e}")

            # 7. Demo Tools Flagged Hospital
            print("7. Capturing 07_demo_tools_flagged_hospital.png...")
            try:
                demo_tools = page.locator('summary:has-text("Demo tools")').first
                if demo_tools.count() > 0:
                    demo_tools.scroll_into_view_if_needed()
                    demo_tools.click()
                    page.wait_for_timeout(1000)
                    beds_input = page.locator('input[aria-label="Set free general beds for this hospital"]').first
                    if beds_input.count() > 0:
                        beds_input.fill("0")
                        apply_sim = page.locator('button:has-text("Apply bed change")').first
                        if apply_sim.count() > 0:
                            apply_sim.click()
                            page.wait_for_timeout(2500)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(1500)
                assert_no_badge_leak(page, "07_demo_tools_flagged_hospital")
                page.screenshot(path=str(SCREENSHOTS_DIR / "07_demo_tools_flagged_hospital.png"))
                print("   [ok] Saved 07_demo_tools_flagged_hospital.png")
                # Reset simulation
                reset_btn = page.locator('button:has-text("Reset to snapshot")').first
                if reset_btn.count() > 0:
                    reset_btn.click()
                    page.wait_for_timeout(1500)
            except Exception as e:
                print(f"   [err] Demo tools capture failed: {e}")

            # 8. Smart Search Result Line
            print("8. Capturing 08_smart_search_result_line.png...")
            try:
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(1000)
                search_input = page.locator('input[aria-label="Tell me what you need"], input[placeholder*="near Patia"]').first
                if search_input.count() > 0:
                    search_input.fill("near Patia, I have an Ayushman card, cheapest first")
                    page.wait_for_timeout(500)
                    apply_btn = page.get_by_role("button", name="Apply", exact=True).first
                    if apply_btn.count() > 0:
                        apply_btn.click()
                        page.wait_for_timeout(3000)
                assert_no_badge_leak(page, "08_smart_search_result_line")
                page.screenshot(path=str(SCREENSHOTS_DIR / "08_smart_search_result_line.png"))
                print("   [ok] Saved 08_smart_search_result_line.png")
            except Exception as e:
                print(f"   [err] Smart search capture failed: {e}")

            # 10. Table Desktop 1440 (no horizontal scroll)
            print("10. Capturing 10_table_desktop_1440_no_scroll.png...")
            try:
                table_elem = page.locator('[data-testid="stDataFrame"], .stDataFrame').first
                table_elem.scroll_into_view_if_needed()
                page.wait_for_timeout(1500)
                assert_no_badge_leak(page, "10_table_desktop_1440_no_scroll")
                table_elem.screenshot(path=str(SCREENSHOTS_DIR / "10_table_desktop_1440_no_scroll.png"))
                print("   [ok] Saved 10_table_desktop_1440_no_scroll.png")
            except Exception as e:
                print(f"   [err] Table capture failed: {e}")

            desktop.close()

            # 9. GPS Location Chip (Playwright geolocation context)
            print("9. Capturing 09_gps_location_chip.png with GPS mock...")
            try:
                gps_context = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    geolocation={"latitude": 20.3540, "longitude": 85.8190, "accuracy": 35},
                    permissions=["geolocation"],
                )
                gps_page = gps_context.new_page()
                gps_page.set_default_timeout(10000)
                gps_page.goto(url)
                gps_page.wait_for_selector(".hospital-card", timeout=25000)
                gps_btn = gps_page.locator('button:has-text("Use my current location")').first
                if gps_btn.count() > 0:
                    gps_btn.click()
                    gps_page.wait_for_timeout(3000)
                assert_no_badge_leak(gps_page, "09_gps_location_chip")
                gps_page.screenshot(path=str(SCREENSHOTS_DIR / "09_gps_location_chip.png"))
                gps_context.close()
                print("   [ok] Saved 09_gps_location_chip.png")
            except Exception as e:
                print(f"   [err] GPS capture failed: {e}")

            # 11. Mobile Viewport (390x844)
            print("11. Capturing 11_full_page_mobile_390.png...")
            try:
                mobile = browser.new_context(
                    viewport={"width": 390, "height": 844},
                    is_mobile=True,
                    user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
                )
                mob_page = mobile.new_page()
                mob_page.set_default_timeout(10000)
                mob_page.goto(url)
                mob_page.wait_for_selector(".hospital-card", timeout=25000)
                mob_page.wait_for_timeout(2500)
                assert_no_badge_leak(mob_page, "11_full_page_mobile_390")
                mob_page.screenshot(path=str(SCREENSHOTS_DIR / "11_full_page_mobile_390.png"), full_page=True)
                mobile.close()
                print("   [ok] Saved 11_full_page_mobile_390.png")
            except Exception as e:
                print(f"   [err] Mobile capture failed: {e}")

            browser.close()

        missing = [f for f in PRODUCED_FILES if not (SCREENSHOTS_DIR / f).exists()]
        if missing:
            print(f"ERROR: Missing screenshots: {missing}")
            return 1
        print(f"All {len(PRODUCED_FILES)} screenshots captured successfully into {SCREENSHOTS_DIR}!")
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
