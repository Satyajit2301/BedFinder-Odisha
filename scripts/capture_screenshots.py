"""Automated screenshot capture using Playwright for BedFinder Odisha v2.2."""
import os
import subprocess
import sys
import time
from pathlib import Path

SCREENSHOTS_DIR = Path("docs/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


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

            # --- DESKTOP VIEWPORT (1366x768) ---
            desktop = browser.new_context(viewport={"width": 1366, "height": 768})
            page = desktop.new_page()

            # 1. Default view
            print("1. Capturing 01_default_view_1366x768.png...")
            page.goto(url)
            page.wait_for_selector(".hospital-card", timeout=25000)
            page.wait_for_timeout(3000)
            page.screenshot(path=str(SCREENSHOTS_DIR / "01_default_view_1366x768.png"), full_page=True)

            # 2. BedScore method
            print("2. Capturing 06_bedscore_method_1366x768.png...")
            bedscore_opt = page.locator('label:has-text("BedScore")')
            if bedscore_opt.count() > 0:
                bedscore_opt.first.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=str(SCREENSHOTS_DIR / "06_bedscore_method_1366x768.png"), full_page=True)

            # 3. Card toggle ON
            print("3. Capturing 04_card_toggle_on_1366x768.png...")
            card_toggle = page.locator('label:has-text("Ayushman")')
            if card_toggle.count() > 0:
                card_toggle.first.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=str(SCREENSHOTS_DIR / "04_card_toggle_on_1366x768.png"), full_page=True)
                card_toggle.first.click()  # reset
                page.wait_for_timeout(1500)

            # 4. What-if expander
            print("4. Capturing 07_whatif_expander_1366x768.png...")
            expander = page.locator('summary:has-text("Simulate a hospital filling up")')
            if expander.count() == 0:
                expander = page.locator('text=Simulate a hospital filling up')
            if expander.count() > 0:
                expander.first.click()
                page.wait_for_timeout(2500)
                page.screenshot(path=str(SCREENSHOTS_DIR / "07_whatif_expander_1366x768.png"), full_page=True)
                expander.first.click()  # close
                page.wait_for_timeout(1000)

            # 5. Invalid manual location
            print("5. Capturing 05_invalid_manual_location_1366x768.png...")
            manual_opt = page.locator('label:has-text("Enter manually")')
            if manual_opt.count() > 0:
                manual_opt.first.click()
                page.wait_for_timeout(2000)
                input_box = page.locator('input[type="text"]').first
                if input_box.count() > 0:
                    input_box.fill("28.6139, 77.2090")
                    input_box.press("Enter")
                    page.wait_for_timeout(2500)
                    page.screenshot(path=str(SCREENSHOTS_DIR / "05_invalid_manual_location_1366x768.png"), full_page=True)

            # Reset back to default landmark
            landmark_opt = page.locator('label:has-text("Select landmark")')
            if landmark_opt.count() > 0:
                landmark_opt.first.click()
                page.wait_for_timeout(2000)

            # 6. Top N = 1 (via slider interaction)
            print("6. Capturing 02_top_n_1_1366x768.png...")
            slider = page.locator('div[role="slider"]')
            if slider.count() > 0:
                slider.first.focus()
                for _ in range(35):
                    slider.first.press("ArrowLeft")
                page.wait_for_timeout(2500)
                page.screenshot(path=str(SCREENSHOTS_DIR / "02_top_n_1_1366x768.png"), full_page=True)

            # 7. Top N = all (32)
            print("7. Capturing 03_top_n_all_1366x768.png...")
            if slider.count() > 0:
                slider.first.focus()
                for _ in range(35):
                    slider.first.press("ArrowRight")
                page.wait_for_timeout(2500)
                page.screenshot(path=str(SCREENSHOTS_DIR / "03_top_n_all_1366x768.png"), full_page=True)

            desktop.close()

            # --- MOBILE VIEWPORT (390x844) ---
            print("8. Capturing 08_mobile_view_390x844.png...")
            mobile = browser.new_context(
                viewport={"width": 390, "height": 844},
                is_mobile=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
            )
            mob_page = mobile.new_page()
            mob_page.goto(url)
            mob_page.wait_for_selector(".hospital-card", timeout=25000)
            mob_page.wait_for_timeout(3000)
            mob_page.screenshot(path=str(SCREENSHOTS_DIR / "08_mobile_view_390x844.png"), full_page=True)
            mobile.close()

            browser.close()

        print(f"All 8 screenshots successfully captured into {SCREENSHOTS_DIR}!")
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
