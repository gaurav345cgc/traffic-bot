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
from behavior import human_like_behavior  # ✅ your behavior

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


def create_proxy_auth_extension(proxy_host, proxy_port, proxy_username, proxy_password, scheme='http', plugin_path='proxy_auth_plugin.zip'):
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
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
                username: "{proxy_username}",
                password: "{proxy_password}"
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


def launch_browser(proxy: dict = None):
    try:
        options = Options()
        options.headless = HEADLESS

        if proxy:
            logger.info(f"Using proxy: {proxy['host']}:{proxy['port']}")
            proxy_extension = create_proxy_auth_extension(
                proxy['host'], proxy['port'], proxy['username'], proxy['password']
            )
            options.add_extension(proxy_extension)
        else:
            proxy_extension = None
            logger.info("No proxy used.")

        # Add stealth and stability flags
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-gpu')

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/110.0.5481.177 Safari/537.36"
        )

        driver = uc.Chrome(options=options)
        driver.set_page_load_timeout(TIMEOUT)

        logger.info("Browser launched successfully.")

        # Clean up proxy extension file if created
        if proxy_extension and os.path.exists(proxy_extension):
            try:
                os.remove(proxy_extension)
                logger.info(f"Deleted proxy extension file: {proxy_extension}")
            except Exception as e:
                logger.warning(f"Could not delete proxy extension file: {e}")

        return driver

    except Exception as e:
        logger.error(f"Failed to launch browser: {e}")
        return None


def get_page_with_retry(url, proxy_manager, max_retries=5):
    last_proxy = None
    for attempt in range(max_retries):
        proxy_str = proxy_manager.get_random_proxy()
        if not proxy_str:
            logger.error("No proxies available. Please check proxies.txt and try again.")
            return None
        proxy = proxy_manager.parse_proxy(proxy_str)
        if not proxy:
            logger.error(f"Failed to parse proxy: {proxy_str}")
            continue

        last_proxy = proxy
        driver = launch_browser(proxy)
        if not driver:
            logger.error("Failed to launch browser with proxy, retrying with next proxy...")
            continue

        try:
            logger.info(f"Attempt {attempt + 1}: Navigating to {url} with proxy {proxy['host']}:{proxy['port']}")
            driver.get(url)

            # Better wait: wait for a key element that reliably indicates page is loaded
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))

            # Your human-like behavior here
            human_like_behavior(driver)

            page_title = driver.title.strip()
            if page_title:
                logger.info(f"Page loaded with title: {page_title}")
            else:
                logger.warning("Page loaded but title is empty, checking content length...")

            page_source = driver.page_source
            if len(page_source) > 500:
                logger.info("Page loaded successfully with sufficient content.")
                return page_source
            else:
                logger.error("Page content too short, retrying with next proxy...")
                with open("debug_page_source.html", "w", encoding="utf-8") as file:
                    file.write(page_source)
                logger.info("Saved page source to debug_page_source.html for analysis.")

        except Exception as e:
            logger.error(f"Error during page load or behavior simulation: {e}")

        finally:
            try:
                driver.quit()
                logger.info("Browser closed successfully.")
            except Exception as e:
                logger.error(f"Error while closing browser: {e}")
            finally:
                try:
                    del driver
                    gc.collect()
                except Exception:
                    pass

    logger.error(f"All {max_retries} attempts failed. Last proxy used: {last_proxy}")
    return None


if __name__ == "__main__":
    proxy_manager = ProxyManager()
    url = "https://eoxs.com/"

    page = get_page_with_retry(url, proxy_manager, max_retries=5)
    if page:
        logger.info("Processing page...")
        # Your page processing logic here
    else:
        logger.error("Failed to load page after retries.")
