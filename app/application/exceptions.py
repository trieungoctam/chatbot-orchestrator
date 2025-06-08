"""
Application Layer Exceptions
Handles application-specific errors and cross-cutting concerns
"""
from typing import Optional, Any, Dict


class ApplicationError(Exception):
    """Base application layer exception"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code or "APPLICATION_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class UseCaseError(ApplicationError):
    """Use case execution error"""

    def __init__(self, use_case: str, message: str, error_code: Optional[str] = None):
        super().__init__(
            message=f"Use case '{use_case}' failed: {message}",
            error_code=error_code or "USE_CASE_ERROR",
            details={"use_case": use_case}
        )


class ValidationError(ApplicationError):
    """DTO validation error"""

    def __init__(self, field: str, value: Any, message: str):
        super().__init__(
            message=f"Validation failed for field '{field}': {message}",
            error_code="VALIDATION_ERROR",
            details={"field": field, "value": str(value)}
        )


class ExternalServiceError(ApplicationError):
    """External service integration error"""

    def __init__(self, service: str, operation: str, message: str, status_code: Optional[int] = None):
        super().__init__(
            message=f"External service '{service}' failed during '{operation}': {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={
                "service": service,
                "operation": operation,
                "status_code": status_code
            }
        )


class ResourceNotFoundError(ApplicationError):
    """Resource not found error"""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} with ID '{resource_id}' not found",
            error_code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class ConcurrencyError(ApplicationError):
    """Concurrency/transaction error"""

    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Concurrency error during '{operation}': {message}",
            error_code="CONCURRENCY_ERROR",
            details={"operation": operation}
        )


class AuthorizationError(ApplicationError):
    """Authorization/permission error"""

    def __init__(self, user_id: str, operation: str, resource: str):
        super().__init__(
            message=f"User '{user_id}' not authorized for operation '{operation}' on '{resource}'",
            error_code="AUTHORIZATION_ERROR",
            details={
                "user_id": user_id,
                "operation": operation,
                "resource": resource
            }
        )


class RateLimitError(ApplicationError):
    """Rate limiting error"""

    def __init__(self, resource: str, limit: int, window: str):
        super().__init__(
            message=f"Rate limit exceeded for '{resource}': {limit} requests per {window}",
            error_code="RATE_LIMIT_ERROR",
            details={
                "resource": resource,
                "limit": limit,
                "window": window
            }
        )


class ConfigurationError(ApplicationError):
    """Configuration/setup error"""

    def __init__(self, component: str, message: str):
        super().__init__(
            message=f"Configuration error in '{component}': {message}",
            error_code="CONFIGURATION_ERROR",
            details={"component": component}
        )