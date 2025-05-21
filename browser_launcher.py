import undetected_chromedriver as uc
import time
import random
import zipfile
import gc
import os
from selenium.webdriver.chrome.options import Options
from loguru import logger
from config import HEADLESS, TIMEOUT
from proxy_manager import ProxyManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from behavior import human_like_behavior  # your custom human behavior logic

# Patch to suppress OSError: [WinError 6]
_original_del = uc.Chrome.__del__
def _safe_del(self):
    try:
        _original_del(self)
    except OSError as e:
        if getattr(e, "winerror", None) == 6:
            pass
        else:
            raise
uc.Chrome.__del__ = _safe_del

# --- Fingerprint Evasion Utils ---

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    ]
    return random.choice(user_agents)

def get_random_window_size():
    return random.choice([(1366, 768), (1920, 1080), (1440, 900), (1600, 900)])

def inject_stealth_scripts(driver):
    try:
        with open("./stealth.min.js", "r", encoding="utf-8") as f:
            script = f.read()
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": script})
        logger.info("Stealth script injected.")
    except Exception as e:
        logger.error(f"Failed to inject stealth script: {e}")

# --- Proxy Auth Extension Creator ---

def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='http', plugin_path='proxy_auth_plugin.zip'):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>",
            "webRequest", "webRequestBlocking"
        ],
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
        return {{authCredentials: {{username: "{proxy_username}", password: "{proxy_password}"}}}};
    }}

    chrome.webRequest.onAuthRequired.addListener(callbackFn, {{urls: ["<all_urls>"]}}, ['blocking']);
    """
    with zipfile.ZipFile(plugin_path, 'w') as zp:
        zp.writestr("manifest.json", manifest_json)
        zp.writestr("background.js", background_js)

    return plugin_path

# --- Browser Launcher ---
def get_random_window_size():
    # Common screen resolutions
    resolutions = [
        (1366, 768), (1440, 900), (1536, 864), (1600, 900), (1680, 1050),
        (1920, 1080), (1280, 800), (1280, 1024), (1400, 1050), (2560, 1440)
    ]
    return random.choice(resolutions)

def launch_browser(proxy: dict = None):
    try:
        options = Options()
        options.headless = HEADLESS

        # Fingerprint Evasion
        user_agent = get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--lang=en-US,en")

        proxy_extension = None
        if proxy:
            logger.info(f"Using proxy: {proxy['host']}:{proxy['port']}")
            proxy_extension = create_proxy_auth_extension(
                proxy['host'], proxy['port'], proxy['username'], proxy['password']
            )
            options.add_extension(proxy_extension)
        else:
            logger.info("No proxy used.")

        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(TIMEOUT)

        inject_stealth_scripts(driver)

        # Set randomized window size AFTER launching driver & stealth injection
        width, height = get_random_window_size()
        driver.set_window_size(width, height)
        logger.info(f"Randomized window size set to {width}x{height}")

        logger.info("Browser launched successfully.")

        if proxy_extension and os.path.exists(proxy_extension):
            os.remove(proxy_extension)
            logger.info(f"Deleted proxy extension file: {proxy_extension}")

        return driver

    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        return None

# --- Retriable Page Loader ---

def get_page_with_retry(url, proxy_manager, max_retries=5):
    last_proxy = None
    for attempt in range(max_retries):
        proxy_str = proxy_manager.get_random_proxy()
        if not proxy_str:
            logger.error("No proxies available. Please check proxies.txt.")
            return None
        proxy = proxy_manager.parse_proxy(proxy_str)
        if not proxy:
            logger.error(f"Failed to parse proxy: {proxy_str}")
            continue

        last_proxy = proxy
        driver = launch_browser(proxy)
        if not driver:
            logger.error("Failed to launch browser. Retrying...")
            continue

        try:
            logger.info(f"Attempt {attempt + 1}: Navigating to {url}")
            driver.get(url)

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
            human_like_behavior(driver)

            if driver.title.strip():
                logger.info(f"Page loaded with title: {driver.title}")
            else:
                logger.warning("Page title is empty.")

            page_source = driver.page_source
            if len(page_source) > 500:
                logger.info("Page loaded with sufficient content.")
                return page_source
            else:
                logger.warning("Page content too short.")
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(page_source)

        except Exception as e:
            logger.error(f"Page load error: {e}")

        finally:
            try:
                driver.quit()
                logger.info("Browser closed.")
            except Exception as e:
                logger.warning(f"Error during browser quit: {e}")
            finally:
                del driver
                gc.collect()

    logger.error(f"All {max_retries} attempts failed. Last proxy used: {last_proxy}")
    return None

# --- Entrypoint ---

if __name__ == "__main__":
    proxy_manager = ProxyManager()
    url = "https://eoxs.com/"

    try:
        while True:
            logger.info("🔁 Starting a new iteration")

            page = get_page_with_retry(url, proxy_manager, max_retries=5)
            if page:
                logger.success("✅ Page loaded successfully!")
                # 🔽 Add processing/parsing logic here
            else:
                logger.error("❌ Failed to load page after retries.")

            # Optional: randomized delay to mimic human behavior
            wait_time = random.randint(30, 120)
            logger.info(f"⏳ Sleeping for {wait_time} seconds...")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        logger.warning("🛑 Manual stop detected. Exiting...")
    except Exception as e:
        logger.exception(f"Unexpected crash: {e}")
