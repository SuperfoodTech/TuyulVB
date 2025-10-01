class ServiceError(Exception):
    """Base exception for all service errors"""
    pass


class AuthenticationError(ServiceError):
    """Raised when service authentication fails"""
    pass


class ConfigurationError(ServiceError):
    """Raised when configuration is invalid"""
    pass


class DataCollectionError(ServiceError):
    """Raised when data collection fails"""
    pass


class ApiError(ServiceError):
    """Raised for API-specific errors, e.g., from Monday.com"""
    pass
