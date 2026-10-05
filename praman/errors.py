"""Exception classes for Praman."""


class PramanError(Exception):
    """Base exception for all Praman errors."""
    pass


class AutocompleteProtocolError(PramanError):
    """Raised when Google Autocomplete returns HTTP 200 but body is not the expected shape.

    The expected shape is a JSON list of at least two elements whose second
    element is a list of suggestion strings: [query, [suggestion, ...], ...].
    A failure to parse is an unmeasured error, NEVER zero demand.
    """
    def __init__(self, message: str, raw_body: str = ""):
        super().__init__(message)
        self.raw_body = raw_body


class BudgetExceededError(PramanError):
    """Raised when query budget or seed ceiling is exceeded in strict mode."""
    pass


class ConfigurationError(PramanError):
    """Raised when configuration, language definitions, or weights are invalid."""
    pass


class SerpAutomationError(PramanError):
    """Base exception for SERP automation errors."""
    pass


class CaptchaDetectedError(SerpAutomationError):
    """Raised when CAPTCHA or unusual traffic is detected on Google SERP."""
    pass


class BrowserDriverError(SerpAutomationError):
    """Raised when Selenium browser/driver is unavailable or fails to initialize."""
    pass
