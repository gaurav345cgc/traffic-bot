import random
import time
from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def scroll_element_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
    time.sleep(0.5)


def is_element_fully_in_viewport(driver, element):
    return driver.execute_script("""
        const rect = arguments[0].getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    """, element)


def smooth_move_to_element(driver, element, steps=10):
    try:
        rect = element.rect
        center_x, center_y = rect['width'] / 2, rect['height'] / 2
        action = ActionChains(driver).move_to_element_with_offset(element, 0, 0).perform()

        for i in range(1, steps + 1):
            offset_x = center_x * (i / steps)
            offset_y = center_y * (i / steps)
            ActionChains(driver).move_to_element_with_offset(element, offset_x, offset_y).perform()
            time.sleep(random.uniform(0.05, 0.12))
    except Exception as e:
        logger.error(f"smooth_move_to_element failed: {e}")
        try:
            ActionChains(driver).move_to_element(element).perform()
        except Exception as fallback_e:
            logger.error(f"Fallback move_to_element also failed: {fallback_e}")


def scroll_and_smooth_move_to_element(driver, element):
    scroll_element_into_view(driver, element)
    if not is_element_fully_in_viewport(driver, element):
        logger.warning("Retrying scroll, element not fully visible.")
        driver.execute_script("window.scrollBy(0, -100);")
        time.sleep(0.5)
        scroll_element_into_view(driver, element)

    if is_element_fully_in_viewport(driver, element):
        smooth_move_to_element(driver, element)
        return True
    else:
        logger.warning("Element still out of viewport after retries.")
        return False


def scroll_and_click(driver, element):
    try:
        scroll_element_into_view(driver, element)
        if not is_element_fully_in_viewport(driver, element):
            driver.execute_script("window.scrollBy(0, -150);")
            time.sleep(0.5)
            scroll_element_into_view(driver, element)

        ActionChains(driver).move_to_element(element).click().perform()
        logger.info(f"Clicked element: <{element.tag_name}> text='{element.text.strip()[:30]}'")
    except Exception as e:
        logger.error(f"scroll_and_click failed: {e}")


def human_scroll(driver, scroll_pause=0.3, max_scrolls=10):
    try:
        for _ in range(random.randint(3, max_scrolls)):
            driver.execute_script(f"window.scrollBy(0, {random.randint(200, 900)});")
            time.sleep(scroll_pause + random.uniform(0.2, 0.6))

        if random.random() > 0.4:
            driver.execute_script("window.scrollBy(0, -300);")
            time.sleep(scroll_pause + random.uniform(0.1, 0.3))

        logger.info("Completed human-like scrolling.")
    except Exception as e:
        logger.error(f"Error in human_scroll: {e}")


def random_delay(min_sec=0.5, max_sec=2.0):
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"Sleeping for {delay:.2f} seconds to simulate human pause")
    time.sleep(delay)


def simulate_hover(driver, max_attempts=5):
    selectors = ["a", "button", "[role='button']", ".hoverable"]
    elements = sum([driver.find_elements(By.CSS_SELECTOR, sel) for sel in selectors], [])

    visible_elements = [el for el in elements if el.is_displayed() and el.size['width'] > 0 and el.size['height'] > 0]

    if not visible_elements:
        logger.warning("No visible hoverable elements.")
        return

    for attempt in range(max_attempts):
        element = random.choice(visible_elements)
        try:
            if not scroll_and_smooth_move_to_element(driver, element):
                raise Exception("Not in viewport")
            logger.info(f"Hovered on <{element.tag_name}>: '{element.text.strip()[:30]}'")
            time.sleep(random.uniform(1, 3))
            break
        except Exception as e:
            logger.error(f"Hover attempt {attempt+1} failed: {e}")
            visible_elements.remove(element)
            if not visible_elements:
                logger.warning("No more hoverable elements.")
                break


def simulate_click(driver, max_attempts=5):
    selectors = ["a[href]", "button", "[role='button']", "input[type='submit']", "input[type='button']"]
    elements = sum([driver.find_elements(By.CSS_SELECTOR, sel) for sel in selectors], [])

    visible_elements = [el for el in elements if el.is_displayed() and el.is_enabled()]

    if not visible_elements:
        logger.warning("No clickable elements found.")
        return

    for attempt in range(max_attempts):
        element = random.choice(visible_elements)
        try:
            if not scroll_and_smooth_move_to_element(driver, element):
                raise Exception("Not in viewport")
            time.sleep(random.uniform(0.2, 0.5))
            element.click()
            logger.info(f"Clicked <{element.tag_name}>: '{element.text.strip()[:30]}'")
            time.sleep(random.uniform(2, 5))
            break
        except Exception as e:
            logger.error(f"Click attempt {attempt+1} failed: {e}")
            visible_elements.remove(element)
            if not visible_elements:
                logger.warning("No more clickable elements.")
                break


def human_like_behavior(driver):
    human_scroll(driver)
    actions = [simulate_hover, simulate_click]
    random.shuffle(actions)

    for action in actions:
        if random.random() < 0.6:
            action(driver)
            time.sleep(random.uniform(1, 3))

    # Always end with one more click to mimic decisive action
    simulate_click(driver)
    time.sleep(random.uniform(3, 6))
