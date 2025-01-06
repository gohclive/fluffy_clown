import random
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.action_chains import ActionChains
from dotenv import load_dotenv
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('checkout_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class CasioCheckoutAutomation:
    def __init__(self, product_url: str, headless: bool = False, keep_browser_open: bool = False):
        self.product_url = product_url
        self.driver = None
        self.headless = headless
        self.keep_browser_open = keep_browser_open
        self.error_occurred = True
        self._load_environment()

    def _load_environment(self) -> None:
        """Load and validate environment variables."""
        load_dotenv()
        required_vars = [
            'USERNAME', 'PASS', 'PHONE', 'POSTCODE',
            'STREET1', 'STREET2', 'CARD_NUMBER',
            'CARD_EXPIRY', 'CARD_CVC'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}")

    def _initialize_driver(self) -> None:
        """Initialize Chrome WebDriver with anti-detection measures."""
        try:
            service = Service('/usr/bin/chromedriver')
            options = Options()

            # Basic options
            options.add_argument("--no-sandbox")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-dev-shm-usage")

            # Mimic real browser
            options.add_argument(
                "--disable-blink-features=AutomationControlled")
            options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # Add realistic user agent
            options.add_argument(
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

            # Add language and geolocation
            options.add_argument('--lang=en-US')
            options.add_argument('--disable-gpu')

            if self.headless:
                options.add_argument("--headless=new")

            self.driver = webdriver.Chrome(service=service, options=options)

            # Remove navigator.webdriver flag
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })

            # Execute stealth JS
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)

            self.driver.implicitly_wait(5)

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def _scroll_to_element(self, element) -> None:
        """Scroll element into view."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                element
            )
        except Exception as e:
            logger.warning(f"Error during scrolling: {str(e)}")

    def _wait_and_click(self, by: By, selector: str, timeout: int = 10) -> bool:
        """Wait for element and click with retry logic."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )

            # Check if element is visible in viewport
            is_visible = self.driver.execute_script("""
                var elem = arguments[0],
                    box = elem.getBoundingClientRect(),
                    cx = box.left + box.width / 2,
                    cy = box.top + box.height / 2,
                    e = document.elementFromPoint(cx, cy);
                for (; e; e = e.parentElement) {
                    if (e === elem)
                        return true;
                }
                return false;
            """, element)

            if not is_visible:
                self._scroll_to_element(element)

            retries = 3
            while retries > 0:
                try:
                    element.click()
                    return True
                except ElementClickInterceptedException:
                    logger.warning(
                        f"Click intercepted, retrying... ({retries} attempts left)")
                    time.sleep(1)
                    retries -= 1
            return False
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {selector}")
            return False

    def _fill_form_field(self, by: By, selector: str, value: str, timeout: int = 10) -> bool:
        """Fill form field with retry logic."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            element.clear()
            element.send_keys(value)
            return True
        except Exception as e:
            logger.error(f"Failed to fill form field {selector}: {str(e)}")
            return False

    def _refresh_and_retry(self, attempts: int = 3, delay: int = 5) -> bool:
        """
        Refresh page and retry finding the add to cart button.

        Args:
            attempts: Number of refresh attempts
            delay: Delay between attempts in seconds

        Returns:
            bool: True if button found, False otherwise
        """
        logger.info(f"Attempting page refresh. Remaining attempts: {attempts}")

        for attempt in range(attempts):
            try:
                self.driver.refresh()
                time.sleep(delay)  # Wait for page to load

                # Try to find the add to cart button
                add_to_cart_btn = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.p-product__btn-addcart a"))
                )

                if add_to_cart_btn.is_displayed() and add_to_cart_btn.is_enabled():
                    logger.info(
                        f"Add to cart button found after {attempt + 1} refresh attempts")
                    return True

            except Exception as e:
                logger.warning(
                    f"Refresh attempt {attempt + 1} failed: {str(e)}")

            if attempt < attempts - 1:  # Don't sleep on last attempt
                time.sleep(delay)

        logger.error(
            "Failed to find add to cart button after all refresh attempts")
        return False

    def add_to_cart(self) -> bool:
        """Add product to cart and proceed to checkout."""
        try:
            logger.info("Navigating to product page...")
            self.driver.get(self.product_url)

            logger.info("Adding to cart...")
            if not self._wait_and_click(By.CSS_SELECTOR, "div.p-product__btn-addcart a"):
                logger.info(
                    "Add to cart button not found. Attempting refresh...")
                if not self._refresh_and_retry():
                    return False
                if not self._wait_and_click(By.CSS_SELECTOR, "div.p-product__btn-addcart a"):
                    return False

            logger.info("Waiting for modal...")
            if not WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "cmp-modal-content"))
            ):
                return False

            logger.info("Finding checkout button...")
            checkout_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "div.cmp-modal-content button.cmp-button:not(.cmp-button-content__close)"))
            )
            checkout_btn.click()

            # Wait for cart page and click proceed
            logger.info("Clicking proceed to checkout...")
            WebDriverWait(self.driver, 10).until(
                EC.url_to_be("https://www.casio.com/sg/checkout/cart")
            )
            proceed_btn = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.btn.checkout"))
            )
            proceed_btn.click()

            return True
        except Exception as e:
            logger.error(f"Error in add_to_cart: {str(e)}")
            return False

    def handle_login(self) -> bool:
        """Handle login process."""
        try:
            logger.info("Proceeding to login...")
            if not self._wait_and_click(By.CSS_SELECTOR, "button[data-role='opc-continue']"):
                return False

            # Handle cookie consent if present
            try:
                self._wait_and_click(
                    By.CSS_SELECTOR,
                    "button#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowallSelection",
                    timeout=5
                )
            except:
                logger.info("No cookie consent needed")

            # Fill login credentials
            if not all([
                self._fill_form_field(
                    By.ID, "username", os.getenv('USERNAME')),
                self._fill_form_field(By.ID, "password", os.getenv('PASS')),
                self._wait_and_click(By.ID, "idpwbtn")
            ]):
                return False

            # Wait for successful login
            WebDriverWait(self.driver, 20).until(
                EC.url_contains("casio.com/sg")
            )
            logger.info("Login successful")
            return True
        except Exception as e:
            logger.error(f"Error in handle_login: {str(e)}")
            return False

    def fill_checkout_details(self) -> bool:
        """Fill checkout form details with smart scrolling."""
        try:
            logger.info("Filling checkout details...")
            form_fields = {
                "telephone": os.getenv('PHONE'),
                "postcode": os.getenv('POSTCODE'),
                "street[0]": os.getenv('STREET1'),
                "street[1]": os.getenv('STREET2')
            }

            def is_in_viewport(element):
                return self.driver.execute_script("""
                    var rect = arguments[0].getBoundingClientRect();
                    return (rect.top >= 0 && rect.bottom <= window.innerHeight);
                """, element)

            def smart_scroll(element):
                if not is_in_viewport(element):
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        element
                    )

            # Fill form fields
            for field, value in form_fields.items():
                try:
                    element = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.NAME, field))
                    )
                    smart_scroll(element)
                    element.clear()
                    element.send_keys(value)

                    if element.get_attribute('value') != value:
                        raise ValueError(
                            f"Value verification failed for {field}")

                except Exception as e:
                    logger.error(f"Failed to fill {field}: {str(e)}")
                    return False

            # Handle continue button
            try:
                button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "button[data-role='opc-continue']"))
                )
                smart_scroll(button)

                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "button[data-role='opc-continue']"))
                ).click()

                return True

            except Exception as e:
                logger.error(f"Failed to click continue: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error in checkout details: {str(e)}")
            return False

    def handle_payment(self) -> bool:
        """Handle Stripe Elements payment form using JavaScript injection."""
        try:
            logger.info("Starting payment process...")

            # Handle billing checkbox
            try:
                checkbox = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.ID, "billing-address-same-as-shipping-stripe_payments"))
                )
                if not checkbox.is_selected():
                    self.driver.execute_script("""
                        var checkbox = arguments[0];
                        checkbox.checked = true;
                        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                    """, checkbox)
                time.sleep(0.5)
                logger.info("Billing checkbox handled")
            except Exception as e:
                logger.warning(f"Billing checkbox handling failed: {str(e)}")

            # Find and switch to Stripe iframe
            stripe_iframe = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//iframe[contains(@name, '__privateStripeFrame')]"))
            )
            self.driver.switch_to.frame(stripe_iframe)
            logger.info("Switched to Stripe iframe")
            time.sleep(2)

            try:
                # Function to simulate typing with JavaScript
                def simulate_typing(element, text, delay=100):
                    """Simulate typing using JavaScript with delays."""
                    for char in text:
                        self.driver.execute_script("""
                            var element = arguments[0];
                            var char = arguments[1];
                            element.value += char;
                            element.dispatchEvent(new Event('input', { bubbles: true }));
                            element.dispatchEvent(new KeyboardEvent('keydown', { key: char }));
                            element.dispatchEvent(new KeyboardEvent('keypress', { key: char }));
                            element.dispatchEvent(new KeyboardEvent('keyup', { key: char }));
                        """, element, char)
                        time.sleep(delay/1000)  # Convert ms to seconds

                # Card Number Field
                card_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "/html/body/div[1]/div/div/div[1]/div/div/div/div/div/div/form/div/div/div[1]/div/div[1]/div/div[1]/input"))
                )
                card_input.click()
                simulate_typing(card_input, os.getenv('CARD_NUMBER'), 200)
                logger.info("Card number entered")
                time.sleep(1.5)

                # Expiry Date Field
                expiry_input = self.driver.find_element(By.XPATH,
                                                        "/html/body/div[1]/div/div/div[1]/div/div/div/div/div/div/form/div/div/div[2]/div/div[1]/div/div/input"
                                                        )
                expiry_input.click()
                simulate_typing(expiry_input, os.getenv('CARD_EXPIRY'), 200)
                logger.info("Expiry date entered")
                time.sleep(1.5)

                # CVV Field
                cvv_input = self.driver.find_element(By.XPATH,
                                                     "/html/body/div[1]/div/div/div[1]/div/div/div/div/div/div/form/div/div/div[3]/div/div[1]/div/div[1]/input"
                                                     )
                cvv_input.click()
                simulate_typing(cvv_input, os.getenv('CARD_CVC'), 220)
                logger.info("CVV entered")
                time.sleep(1.5)

                # Switch back to main content
                self.driver.switch_to.default_content()
                logger.info("Switched back to main content")

                # Wait for Stripe to process
                time.sleep(2)

                return True

            except Exception as e:
                logger.error(f"Error filling card details: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Payment handling error: {str(e)}")
            return False

        finally:
            try:
                self.driver.switch_to.default_content()
                logger.info("Ensured return to main content")
            except:
                pass

    # def handle_order_placement(self) -> bool:
    #     """Handle the final review and order placement."""
    #     try:
    #         logger.info("Proceeding to place order...")

    #         # Click the place order button
    #         if not self._wait_and_click(
    #             By.CSS_SELECTOR,
    #             "button.btn.btn-l.is-submit.jp-place-order"
    #         ):
    #             return False

    #         logger.info("Order placed successfully")
    #         return True

    #     except Exception as e:
    #         logger.error(f"Error in order placement: {str(e)}")
    #        return False

    def run_checkout(self) -> bool:
        """Execute the complete checkout process."""
        try:
            self._initialize_driver()

            steps = [
                self.add_to_cart,
                self.handle_login,
                self.fill_checkout_details,
                self.handle_payment,
                # self.handle_order_placement
            ]

            for step in steps:
                if not step():
                    logger.error(f"Checkout failed at step: {step.__name__}")
                    return False
                time.sleep(1)  # Small delay between steps

            logger.info("Checkout process completed successfully")
            return True

        except Exception as e:
            self.error_occurred = True
            logger.error(f"Unexpected error during checkout: {str(e)}")
            return False
        finally:
            if self.driver and not self.keep_browser_open and not self.error_occurred:
                # self.driver.quit()
                try:
                    while True:
                        pass
                except KeyboardInterrupt:
                    self.driver.quit()
                print("keep browser open")
            elif self.error_occurred:
                logger.info(
                    "Keeping browser open due to error for debugging...")


def main():
    product_url = "https://www.casio.com/sg/watches/casio/product.CA-53WB-8B/"
    automation = CasioCheckoutAutomation(
        product_url=product_url,
        headless=False
    )

    try:
        success = automation.run_checkout()
        if success:
            logger.info("Checkout automation completed successfully")
            while True:  # Keep browser open
                pass
        else:
            logger.error("Checkout automation failed")
    except KeyboardInterrupt:
        logger.info("Automation stopped by user")
    except Exception as e:
        logger.error(f"Automation failed with error: {str(e)}")
    finally:
        user_input = input("Close browser? (y/n): ")
        if user_input.lower() == 'y' and automation.driver:
            automation.driver.quit()


if __name__ == "__main__":
    main()
