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
    def __init__(self, product_url: str, headless: bool = False, keep_browser_open: bool = True):
        self.product_url = product_url
        self.driver = None
        self.headless = headless
        self.keep_browser_open = keep_browser_open
        self.error_occurred = False
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

            # Add window size randomization
            window_sizes = [
                (1920, 1080),
                (1366, 768),
                (1536, 864),
                (1440, 900),
                (1280, 720)
            ]
            window_size = random.choice(window_sizes)
            options.add_argument(
                f"--window-size={window_size[0]},{window_size[1]}")

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

            # Set random viewport
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'mobile': False,
                'width': window_size[0],
                'height': window_size[1],
                'deviceScaleFactor': 1,
            })

            self.driver.implicitly_wait(5)

        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def _wait_and_click(self, by: By, selector: str, timeout: int = 10) -> bool:
        """Wait for element and click with retry logic."""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
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
        """Fill checkout form details."""
        try:
            logger.info("Filling checkout details...")
            # Fill address details
            form_fields = {
                "telephone": os.getenv('PHONE'),
                "postcode": os.getenv('POSTCODE'),
                "street[0]": os.getenv('STREET1'),
                "street[1]": os.getenv('STREET2')
            }

            for field, value in form_fields.items():
                if not self._fill_form_field(By.NAME, field, value):
                    return False

            # Proceed to next step
            return self._wait_and_click(
                By.CSS_SELECTOR,
                "button[data-role='opc-continue']"
            )
        except Exception as e:
            logger.error(f"Error in fill_checkout_details: {str(e)}")
            return False

    def handle_payment(self) -> bool:
        """Handle payment form filling."""
        try:
            logger.info("Filling payment details...")
            payment_fields = {
                "Field-numberInput": os.getenv('CARD_NUMBER'),
                "Field-expiryInput": os.getenv('CARD_EXPIRY'),
                "Field-cvcInput": os.getenv('CARD_CVC')
            }

            for field_id, value in payment_fields.items():
                if not self._fill_form_field(By.ID, field_id, value):
                    return False

            return True
        except Exception as e:
            logger.error(f"Error in handle_payment: {str(e)}")
            return False

    def run_checkout(self) -> bool:
        """Execute the complete checkout process."""
        try:
            self._initialize_driver()

            steps = [
                self.add_to_cart,
                self.handle_login,
                self.fill_checkout_details,
                self.handle_payment
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
                self.driver.quit()
            elif self.error_occurred:
                logger.info(
                    "Keeping browser open due to error for debugging...")


def main():
    product_url = "https://www.casio.com/sg/watches/gshock/product.DW-5610UU-3/"
    automation = CasioCheckoutAutomation(
        product_url=product_url,
        headless=False  # Set to True for headless mode
    )

    try:
        success = automation.run_checkout()
        if success:
            logger.info("Checkout automation completed successfully")
        else:
            logger.error("Checkout automation failed")
    except KeyboardInterrupt:
        logger.info("Automation stopped by user")
    except Exception as e:
        logger.error(f"Automation failed with error: {str(e)}")
    # finally:
    #     if automation.driver:
    #         automation.driver.quit()


if __name__ == "__main__":
    main()
