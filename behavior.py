import random
import time
from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def scroll_element_into_view(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", element)
    time.sleep(0.5)  # allow layout adjustments


def is_element_fully_in_viewport(driver, element):
    return driver.execute_script("""
        const elem = arguments[0];
        const rect = elem.getBoundingClientRect();
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
        width = rect['width']
        height = rect['height']

        # Calculate center of the element
        center_x = width / 2
        center_y = height / 2

        action = ActionChains(driver)

        # Start by moving mouse to top-left corner of element (offset 0,0)
        action.move_to_element_with_offset(element, 0, 0).perform()
        action.reset_actions()

        # Move cursor smoothly to center of the element in small steps
        step_x = center_x / steps
        step_y = center_y / steps

        for i in range(1, steps + 1):
            offset_x = step_x * i
            offset_y = step_y * i
            action.move_to_element_with_offset(element, offset_x, offset_y).perform()
            time.sleep(random.uniform(0.05, 0.12))
            action.reset_actions()

    except Exception as e:
        logger.error(f"smooth_move_to_element failed: {e}")
        # Fallback: move directly to element center
        try:
            ActionChains(driver).move_to_element(element).perform()
        except Exception as fallback_e:
            logger.error(f"Fallback move_to_element also failed: {fallback_e}")



def scroll_and_smooth_move_to_element(driver, element):
    scroll_element_into_view(driver, element)
    if not is_element_fully_in_viewport(driver, element):
        logger.warning("Element still not fully visible after scrollIntoView, scrolling again.")
        driver.execute_script("window.scrollBy(0, -100);")  # scroll up a bit and try again
        time.sleep(0.5)
        scroll_element_into_view(driver, element)
        time.sleep(0.5)
        if not is_element_fully_in_viewport(driver, element):
            logger.warning("Element still out of viewport after retry, skipping smooth move.")
            return False

    smooth_move_to_element(driver, element)
    return True


def scroll_and_click(driver, element):
    try:
        scroll_element_into_view(driver, element)
        if not is_element_fully_in_viewport(driver, element):
            logger.warning("Element still not fully in viewport after scrollIntoView. Scrolling more aggressively.")
            driver.execute_script("window.scrollBy(0, 0);")  # fallback scroll to top
            time.sleep(0.5)
            scroll_element_into_view(driver, element)
            time.sleep(0.5)

        action = ActionChains(driver)
        action.move_to_element(element).click().perform()
        logger.info(f"Clicked element: <{element.tag_name}> text='{element.text}'")
    except Exception as e:
        logger.error(f"scroll_and_click failed: {e}")


def human_scroll(driver, scroll_pause=0.3, max_scrolls=10):
    """
    Scroll down the page in random increments with small pauses to mimic human behavior.
    """
    try:
        for _ in range(random.randint(3, max_scrolls)):
            scroll_amount = random.randint(200, 900)
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(scroll_pause + random.uniform(0.2, 0.6))

        if random.random() > 0.4:
            driver.execute_script("window.scrollBy(0, -300);")
            time.sleep(scroll_pause + random.uniform(0.1, 0.3))

        logger.info("Completed human-like scrolling.")

    except Exception as e:
        logger.error(f"Error in human_scroll: {e}")


def random_delay(min_sec=0.5, max_sec=2.0):
    """
    Pause execution for a random amount of time between min_sec and max_sec.
    """
    delay = random.uniform(min_sec, max_sec)
    logger.info(f"Sleeping for {delay:.2f} seconds to simulate human pause")
    time.sleep(delay)


def simulate_hover(driver, max_attempts=5):
    """
    Randomly hover over visible hoverable elements on the page.
    """
    hoverable_selectors = ["a", "button", "[role='button']", ".hoverable"]

    elements = []
    for sel in hoverable_selectors:
        elements.extend(driver.find_elements(By.CSS_SELECTOR, sel))

    visible_elements = [
        el for el in elements if el.is_displayed() and el.size['width'] > 0 and el.size['height'] > 0
    ]

    if not visible_elements:
        logger.warning("No visible hoverable elements found.")
        return

    for attempt in range(max_attempts):
        element = random.choice(visible_elements)
        try:
            moved = scroll_and_smooth_move_to_element(driver, element)
            if not moved:
                raise Exception("Skipping hover due to viewport issues")

            logger.info(f"Hovered over element: <{element.tag_name}> with text '{element.text[:30]}'")
            time.sleep(random.uniform(1, 3))  # linger after hover
            break
        except Exception as e:
            logger.error(f"Hover attempt {attempt + 1} failed: {e}")
            visible_elements.remove(element)
            if not visible_elements:
                logger.warning("No more elements to hover.")
                break


def simulate_click(driver, max_attempts=5):
    """
    Randomly click on visible and enabled clickable elements.
    """
    clickable_selectors = [
        "a[href]", "button", "[role='button']", "input[type='submit']", "input[type='button']"
    ]

    elements = []
    for sel in clickable_selectors:
        elements.extend(driver.find_elements(By.CSS_SELECTOR, sel))

    visible_elements = [el for el in elements if el.is_displayed() and el.is_enabled()]

    if not visible_elements:
        logger.warning("No clickable elements found.")
        return

    for attempt in range(max_attempts):
        element = random.choice(visible_elements)
        try:
            moved = scroll_and_smooth_move_to_element(driver, element)
            if not moved:
                raise Exception("Skipping click due to viewport issues")

            time.sleep(random.uniform(0.2, 0.5))  # pause before click
            element.click()
            logger.info(f"Clicked element: <{element.tag_name}> with text '{element.text[:30]}'")
            time.sleep(random.uniform(2, 5))
            break
        except Exception as e:
            logger.error(f"Click attempt {attempt + 1} failed: {e}")
            visible_elements.remove(element)
            if not visible_elements:
                logger.warning("No more clickable elements.")
                break


def human_like_behavior(driver):
    """
    Run the full suite of human-like behaviors: scrolling, hovering, clicking, and delays.
    """
    human_scroll(driver)

    actions = [simulate_hover, simulate_click]
    random.shuffle(actions)

    for action in actions:
        if random.random() < 0.6:  # 60% chance to perform each action
            action(driver)
            time.sleep(random.uniform(1, 3))
    simulate_click(driver)

    # Final thinking pause
    time.sleep(random.uniform(3, 6))
