from loguru import logger
from selenium.webdriver.common.by import By

def detect_captcha(driver) -> bool:
    """Detect if a CAPTCHA is present on the page."""
    try:
        # Check common CAPTCHA indicators
        captcha_keywords = ['captcha', 'hcaptcha', 'recaptcha', 'cf-challenge']
        page_source = driver.page_source.lower()

        if any(keyword in page_source for keyword in captcha_keywords):
            logger.warning("CAPTCHA detected based on keyword in page source.")
            return True

        # Check for common CAPTCHA elements
        selectors = [
            "iframe[src*='recaptcha']",  # reCAPTCHA v2
            "div[id*='captcha']",        # generic
            "input[name='captcha']",     # text entry CAPTCHA
            "div.h-captcha",             # hCaptcha
        ]

        for selector in selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                logger.warning(f"CAPTCHA element detected via selector: {selector}")
                return True

        return False

    except Exception as e:
        logger.error(f"Error during CAPTCHA detection: {e}")
        return False


def detect_block_or_rate_limit(driver) -> bool:
    """Detect if the page is blocked, rate-limited or has no usable content."""
    try:
        # Look for 403/429-like content
        block_indicators = ['access denied', 'error 403', 'error 429', 'temporarily unavailable', 'you have been blocked']
        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()

        for keyword in block_indicators:
            if keyword in body_text:
                logger.warning(f"Block/Rate-limit indicator detected: '{keyword}'")
                return True

        # Check for blank or near-empty page
        if len(body_text.strip()) < 100:
            logger.warning("Page appears nearly blank or empty — potential block or challenge.")
            return True

        return False

    except Exception as e:
        logger.error(f"Error during block/rate-limit detection: {e}")
        return False
