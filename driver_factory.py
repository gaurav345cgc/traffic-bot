# driver_factory.py

import os
import zipfile
import random
import gc
from loguru import logger
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options

# === SETTINGS ===
HEADLESS = False  # Set True for background mode
STEALTH_JS_PATH = "stealth.min.js"  # Optional: Inject JS for extra evasion


# === Utilities ===

def random_user_agent():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.5481.100 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.1 Safari/605.1.15",
    ]
    return random.choice(agents)


def random_window_size():
    return random.choice([(1366, 768), (1920, 1080), (1440, 900), (1600, 1200)])


def create_proxy_auth_extension(proxy, plugin_path="proxy_auth_plugin.zip"):
    proxy_host = proxy['host']
    proxy_port = proxy['port']
    proxy_user = proxy['username']
    proxy_pass = proxy['password']
    scheme = proxy.get("scheme", "http")

    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
        "background": { "scripts": ["background.js"] },
        "minimum_chrome_version":"22.0.0"
    }
    """

    background_js = f"""
    var config = {{
        mode: "fixed_servers",
        rules: {{
          singleProxy: {{
            scheme: "{scheme}",
            host: "{proxy_host}",
            port: parseInt({proxy_port})
          }},
          bypassList: ["localhost"]
        }}
    }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});

    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{proxy_user}",
                password: "{proxy_pass}"
            }}
        }};
    }}

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        {{urls: ["<all_urls>"]}},
        ['blocking']
    );
    """

    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path


# === Main Factory Function ===

def create_stealth_chrome_driver(proxy=None):
    options = Options()
    user_agent = random_user_agent()
    width, height = random_window_size()

    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    options.add_argument(f"--window-size={width},{height}")

    if HEADLESS:
        options.add_argument("--headless=chrome")


    plugin_path = None
    if proxy:
        logger.info(f"Using proxy: {proxy['host']}:{proxy['port']}")
        plugin_path = create_proxy_auth_extension(proxy)
        options.add_extension(plugin_path)
    else:
        logger.info("No proxy used.")

    try:
        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(30)

        # Inject optional JS evasion (if you have stealth.min.js)
        if os.path.exists(STEALTH_JS_PATH):
            with open(STEALTH_JS_PATH, 'r') as js_file:
                stealth_js = js_file.read()
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": stealth_js
            })

        logger.success("✅ Stealth Chrome driver launched successfully.")

        if plugin_path and os.path.exists(plugin_path):
            os.remove(plugin_path)

        return driver

    except Exception as e:
        logger.error(f"Failed to launch stealth driver: {e}")
        return None


def destroy_driver(driver):
    try:
        driver.quit()
        logger.info("Browser closed.")
    except Exception as e:
        logger.warning(f"Error closing browser: {e}")
    finally:
        del driver
        gc.collect()
