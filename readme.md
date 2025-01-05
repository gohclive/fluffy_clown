# Casio G-Shock Checkout Automation

An automated checkout script for Casio G-Shock watches using Selenium WebDriver. This script automates the entire purchase process from adding to cart through payment completion.

## Features

- Automated browser control using Selenium WebDriver
- Robust error handling and retry mechanisms
- Comprehensive logging system
- Environment variable configuration
- Headless mode support
- Cookie consent handling
- Configurable timeouts and retry attempts

## Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- ChromeDriver matching your Chrome version
- Virtual environment (recommended)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd casio-checkout-automation
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Configure ChromeDriver:

- Download ChromeDriver matching your Chrome version from: https://sites.google.com/chromium.org/driver/
- Place the chromedriver executable in `/usr/bin/` (Linux/Mac) or add to PATH (Windows)

## Configuration

1. Create a `.env` file in the project root with the following variables:

```env
USERNAME=your_email@example.com
PASS=your_password
PHONE=your_phone_number
POSTCODE=your_postcode
STREET1=your_street_address_line_1
STREET2=your_street_address_line_2
CARD_NUMBER=your_card_number
CARD_EXPIRY=your_card_expiry_MMYY
CARD_CVC=your_card_cvc
```

## Usage

1. Basic usage:

```python
from checkout_automation import CasioCheckoutAutomation

product_url = "https://www.casio.com/sg/watches/gshock/product.DW-5610UU-3/"
automation = CasioCheckoutAutomation(product_url=product_url)
automation.run_checkout()
```

2. With headless mode:

```python
automation = CasioCheckoutAutomation(product_url=product_url, headless=True)
```

## Logging

- Logs are written to `checkout_automation.log`
- Console output shows real-time progress
- Log level can be configured in the script

## Error Handling

The script includes comprehensive error handling for:

- Network issues
- Element loading timeouts
- Click interceptions
- Form filling errors
- Payment processing issues

## Troubleshooting

1. ChromeDriver version mismatch:

```bash
# Check Chrome version
google-chrome --version

# Download matching ChromeDriver version and update path
```

2. Environment variables not loading:

- Verify `.env` file exists in project root
- Check file permissions
- Ensure all required variables are set

3. Common errors and solutions:

- Timeout errors: Increase timeout values in script
- Element not found: Update selectors if website layout changed
- Click intercepted: Adjust wait times or scroll logic

## Advanced Usage

### Custom Timeout Configuration

```python
automation = CasioCheckoutAutomation(
    product_url=product_url,
    headless=True,
    timeout=20  # Custom timeout in seconds
)
```

### Error Recovery

The script includes automatic retry mechanisms for common failures:

- Click attempts: 3 retries
- Form filling: 2 retries
- Navigation: 2 retries

### Debug Mode

```python
automation = CasioCheckoutAutomation(
    product_url=product_url,
    debug=True  # Enables verbose logging
)
```
