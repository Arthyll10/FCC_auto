import sys
import traceback
from playwright.sync_api import sync_playwright, TimeoutError

BASE_URL = "https://www.freecodecamp.org/learn/2022/responsive-web-design/learn-the-css-box-model-by-building-a-rothko-painting/step-"
START_STEP = 31
END_STEP = 100
USER_DATA_DIR = "./user_data"


def handle_donation_modal(page):
    """Waits for the donation modal delay timer to finish and clicks 'Ask me later'.
    Returns True if a modal was handled, False otherwise."""
    try:
        modal = page.locator('div[class*="donation-modal"], [id*="headlessui-dialog-panel"]').first
        if modal.is_visible():
            print("Donation modal detected. Waiting for 'Ask me later' button timer (25-30s)...")
            ask_later_btn = page.locator('button.close-button:has-text("Ask me later"), button:has-text("Ask me later")').first
            
            # Wait up to 35 seconds for the timer to finish and the button to become visible
            ask_later_btn.wait_for(state="visible", timeout=35000)
            ask_later_btn.click(force=True)
            print("'Ask me later' clicked successfully.")
            page.wait_for_timeout(500)
            return True
    except TimeoutError:
        print("Timed out waiting for 'Ask me later' button.")
    except Exception:
        pass
    return False


def isolate_single_tab(page, target_index):
    handle_donation_modal(page)
    page.wait_for_selector(".react-monaco-editor-container", timeout=15000)

    tabs = page.locator(".monaco-editor-tabs button")
    tab_count = tabs.count()

    if tab_count > 1 and target_index < tab_count:
        target_tab = tabs.nth(target_index)
        if target_tab.get_attribute("aria-expanded") == "false":
            target_tab.dispatch_event("click")
            page.wait_for_timeout(200)

        for j in range(tab_count):
            if j != target_index:
                other_tab = tabs.nth(j)
                if other_tab.get_attribute("aria-expanded") == "true":
                    other_tab.dispatch_event("click")
                    page.wait_for_timeout(300)

    input_area = page.locator("textarea.inputarea").first
    input_area.focus()

    view_lines = page.locator(".monaco-editor .view-lines").first
    if view_lines.is_visible():
        view_lines.click(force=True)

    page.wait_for_timeout(100)


def copy_and_paste_tab(scout_page, worker_page, tab_index, modifier):
    # 1. SCOUT: Isolate tab, focus, copy initial solution
    scout_page.bring_to_front()
    isolate_single_tab(scout_page, tab_index)

    scout_page.keyboard.press(f"{modifier}+A")
    scout_page.keyboard.press(f"{modifier}+C")
    scout_page.wait_for_timeout(100)

    try:
        scout_code = scout_page.evaluate("navigator.clipboard.readText()")
    except Exception:
        scout_code = ""

    if not scout_code or not scout_code.strip():
        print(f"  -> Tab index {tab_index} on Scout is empty. Skipping paste.")
        return

    # 2. WORKER: Bring to front and handle any paywall timers
    worker_page.bring_to_front()
    paywall_encountered = handle_donation_modal(worker_page)

    worker_tabs = worker_page.locator(".monaco-editor-tabs button")
    if worker_tabs.count() > 0 and tab_index >= worker_tabs.count():
        print(f"  -> Worker does not have Tab index {tab_index}. Skipping paste.")
        return

    isolate_single_tab(worker_page, tab_index)

    # 3. WORKER: Copy existing code to perform diff check
    worker_page.keyboard.press(f"{modifier}+A")
    worker_page.keyboard.press(f"{modifier}+C")
    worker_page.wait_for_timeout(100)

    try:
        worker_code = worker_page.evaluate("navigator.clipboard.readText()")
    except Exception:
        worker_code = ""

    # 4. REDUNDANCY CHECK: Skip paste if worker code is already identical to scout code
    if not paywall_encountered and scout_code.strip() == worker_code.strip():
        print(f"  -> Tab index {tab_index} code is already identical. Skipping paste.")
        return

    print(f"  -> Content diff detected for Tab index {tab_index}. Pasting updated code...")

    # Restore scout_code to clipboard before executing paste hotkey
    try:
        worker_page.evaluate("text => navigator.clipboard.writeText(text)", scout_code)
        worker_page.wait_for_timeout(100)
    except Exception:
        # Fallback: re-copy from Scout if clipboard write API call fails
        scout_page.bring_to_front()
        isolate_single_tab(scout_page, tab_index)
        scout_page.keyboard.press(f"{modifier}+A")
        scout_page.keyboard.press(f"{modifier}+C")
        scout_page.wait_for_timeout(200)
        worker_page.bring_to_front()
        isolate_single_tab(worker_page, tab_index)

    worker_page.keyboard.press(f"{modifier}+A")
    worker_page.keyboard.press(f"{modifier}+V")
    worker_page.wait_for_timeout(200)


def sync_all_tabs(scout_page, worker_page, modifier):
    scout_page.bring_to_front()
    handle_donation_modal(scout_page)
    scout_page.wait_for_selector(".react-monaco-editor-container", timeout=15000)

    scout_tabs = scout_page.locator(".monaco-editor-tabs button")
    scout_tab_count = scout_tabs.count()

    if scout_tab_count > 1:
        print(f"Detected {scout_tab_count} file tabs on Scout. Syncing valid tabs...")
        for i in range(scout_tab_count):
            tab_name = scout_tabs.nth(i).text_content().replace("Editor", "").strip()
            print(f"  -> Checking and syncing Tab {i + 1}/{scout_tab_count} ({tab_name})...")
            copy_and_paste_tab(scout_page, worker_page, i, modifier)
    else:
        print("Scout has 1 tab. Executing direct single-tab sync...")
        copy_and_paste_tab(scout_page, worker_page, 0, modifier)


def run():
    modifier = "Meta" if sys.platform == "darwin" else "Control"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            slow_mo=150,
            args=["--disable-blink-features=AutomationControlled"],
            permissions=["clipboard-read", "clipboard-write"],
            viewport={"width": 1280, "height": 800}
        )

        worker_page = context.pages[0] if context.pages else context.new_page()
        scout_page = context.new_page()

        try:
            initial_url = f"{BASE_URL}{START_STEP}"
            print(f"Worker initial load: {initial_url}")
            worker_page.goto(initial_url, wait_until="load")
            handle_donation_modal(worker_page)

            for step in range(START_STEP, END_STEP + 1):
                next_step = step + 1
                next_url = f"{BASE_URL}{next_step}"
                print(f"\n--- Processing Step {step} ---")

                print(f"Scout: Fetching solution from Step {next_step}...")
                scout_page.bring_to_front()
                scout_response = scout_page.goto(next_url, wait_until="load")
                handle_donation_modal(scout_page)

                if scout_response and scout_response.status == 404:
                    print(f"Step {next_step} does not exist. Halting execution.")
                    break

                sync_all_tabs(scout_page, worker_page, modifier)

                worker_page.bring_to_front()
                handle_donation_modal(worker_page)
                print("Worker: Submitting check...")

                check_btn = worker_page.locator('[data-playwright-test-label="independentLowerJaw-check-button"]')
                check_btn.wait_for(state="visible", timeout=10000)
                check_btn.click(force=True)

                # Check if donation modal triggers right after clicking submit
                handle_donation_modal(worker_page)

                try:
                    modal_btn = worker_page.locator(
                        "button:has-text('Submit and continue'), "
                        "button:has-text('Submit and go to next challenge'), "
                        "[data-playwright-test-label='submit-and-go-to-next-challenge']"
                    ).first

                    modal_btn.wait_for(state="visible", timeout=8000)
                    modal_btn.click(force=True)

                    worker_page.wait_for_url(f"**/*step-{next_step}", timeout=10000)
                    print(f"Worker: Advanced to Step {next_step}.")
                except TimeoutError:
                    handle_donation_modal(worker_page)
                    print(f"\n[ERROR] Worker: Step {step} check failed or modal timed out.")
                    worker_page.screenshot(path=f"error_step_{step}.png")
                    print(f"Saved screenshot to error_step_{step}.png")
                    input("\n>>> Execution paused for debugging. Press ENTER to close...")
                    break

        except KeyboardInterrupt:
            print("\nProcess interrupted by user.")
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Execution failed with exception:\n{e}")
            traceback.print_exc()
            input("\n>>> Execution paused due to crash. Press ENTER to close...")
        finally:
            context.close()
            print("Browser context closed safely.")


if __name__ == "__main__":
    run()