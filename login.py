from playwright.sync_api import sync_playwright

USER_DATA_DIR = "./user_data"

def run():
    with sync_playwright() as p:
        # Launch persistent context to save local storage and cookies
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            permissions=["clipboard-read", "clipboard-write"],
            viewport={"width": 1280, "height": 800}
        )

        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.freecodecamp.org/signin")

        print("\n>>> Chromium is open.")
        print(">>> Sign in to your freeCodeCamp account in the browser window.")
        input(">>> Press ENTER in this terminal ONLY AFTER you have successfully signed in...")

        context.close()
        print("Session saved successfully to ./user_data")

if __name__ == "__main__":
    run()