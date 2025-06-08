"""
Domain Exceptions - Business rule violations và domain errors
"""
from typing import Optional, Dict, Any


class DomainError(Exception):
    """Base domain exception for business rule violations"""

    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class BusinessRuleViolationError(DomainError):
    """Thrown when a business rule is violated"""

    def __init__(self, rule_name: str, message: str, entity_id: Optional[str] = None):
        super().__init__(
            message=f"Business rule '{rule_name}' violated: {message}",
            error_code=f"BUSINESS_RULE_{rule_name.upper()}",
            details={"rule_name": rule_name, "entity_id": entity_id}
        )
        self.rule_name = rule_name
        self.entity_id = entity_id


class EntityNotFoundError(DomainError):
    """Thrown when an entity cannot be found"""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} with ID '{entity_id}' not found",
            error_code="ENTITY_NOT_FOUND",
            details={"entity_type": entity_type, "entity_id": entity_id}
        )
        self.entity_type = entity_type
        self.entity_id = entity_id


class InvalidOperationError(DomainError):
    """Thrown when an operation is invalid in current state"""

    def __init__(self, operation: str, current_state: str, message: str):
        super().__init__(
            message=f"Operation '{operation}' invalid in state '{current_state}': {message}",
            error_code="INVALID_OPERATION",
            details={"operation": operation, "current_state": current_state}
        )
        self.operation = operation
        self.current_state = current_state


class ConcurrencyError(DomainError):
    """Thrown when concurrent access conflicts occur"""

    def __init__(self, resource: str, message: str):
        super().__init__(
            message=f"Concurrency conflict on '{resource}': {message}",
            error_code="CONCURRENCY_CONFLICT",
            details={"resource": resource}
        )
        self.resource = resource


class ResourceLimitExceededError(DomainError):
    """Thrown when resource limits are exceeded"""

    def __init__(self, resource_type: str, limit: int, current: int):
        super().__init__(
            message=f"{resource_type} limit exceeded: {current}/{limit}",
            error_code="RESOURCE_LIMIT_EXCEEDED",
            details={"resource_type": resource_type, "limit": limit, "current": current}
        )
        self.resource_type = resource_type
        self.limit = limit
        self.current = current