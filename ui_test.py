import time
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=500)
        page = browser.new_page()

        # Listen to console and errors
        page.on("console", lambda msg: print(f"[Browser Console] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda err: print(f"[Browser Error] {err}"))

        print("Navigating to dashboard...")
        page.goto("http://127.0.0.1:8000/")
        time.sleep(2)

        pages_to_test = [
            ("workflow", "Workflow", lambda: (
                page.fill("#workflow-input", "Write a python script to reverse a string"),
                page.click("#workflow-run"),
                page.wait_for_selector(".result-panel", timeout=30000)
            )),
            ("research", "Research", lambda: (
                page.fill("#research-task", "How does LangGraph compare to AutoGen?"),
                page.click("button[type='submit']"),
                page.wait_for_selector(".result-panel", timeout=30000)
            )),
            ("career", "Career", lambda: (
                page.fill("#career-task", "I want to become a frontend engineer. Here is my resume: ..."),
                page.click("button[type='submit']"),
                page.wait_for_selector(".result-panel", timeout=30000)
            )),
            ("code-review", "Code Review", lambda: (
                page.fill("#code-input", "def hello(): print('hello')"),
                page.click("button[type='submit']"),
                page.wait_for_selector(".result-panel", timeout=30000)
            )),
            ("evaluator", "Evaluator", lambda: (
                page.fill("#eval-text", "The code looks good and secure."),
                page.click("button[type='submit']"),
                page.wait_for_selector(".result-panel", timeout=30000)
            )),
        ]

        for page_id, name, test_func in pages_to_test:
            print(f"--- Testing {name} ---")
            try:
                page.click(f"a[data-page='{page_id}']")
                time.sleep(2)
                test_func()
                print(f"Success for {name}")
                time.sleep(2)
            except Exception as e:
                print(f"Error testing {name}: {e}")
        
        browser.close()

if __name__ == "__main__":
    run_test()
