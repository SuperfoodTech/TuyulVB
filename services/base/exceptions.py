class ServiceError(Exception):
    """Base class for exceptions in this module."""
    pass


class AuthenticationError(ServiceError):
    """Raised when authentication fails."""
    pass


class APIError(ServiceError):
    """Raised for API-specific errors."""
    pass


class ConfigurationError(ServiceError):
    """Raised for configuration-related errors."""
    pass


class BrowserError(ServiceError):
    """Raised for browser automation errors."""
    pass
