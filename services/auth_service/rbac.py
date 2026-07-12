"""Small, explicit role-permission matrix for dashboard endpoints."""

from __future__ import annotations

from dataclasses import dataclass

from services.auth_service.models import AppRole


@dataclass(frozen=True)
class AccessRule:
    method: str
    prefix: str
    roles: frozenset[AppRole]


READ_ROLES = frozenset({"caregiver", "doctor", "admin"})
WRITE_FEEDBACK_ROLES = frozenset({"caregiver", "doctor", "admin"})
ACKNOWLEDGE_ROLES = frozenset({"caregiver", "admin"})

RULES = (
    AccessRule("POST", "/api/events/", ACKNOWLEDGE_ROLES),
    AccessRule("POST", "/api/feedback/generate", WRITE_FEEDBACK_ROLES),
    AccessRule("GET", "/api/", READ_ROLES),
)


def is_allowed(role: AppRole, method: str, path: str) -> bool:
    normalized_method = method.upper()
    for rule in RULES:
        if normalized_method == rule.method and path.startswith(rule.prefix):
            return role in rule.roles
    return False


def can_open_websocket(role: AppRole) -> bool:
    return role in READ_ROLES
