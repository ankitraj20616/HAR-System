from services.auth_service.rbac import can_open_websocket, is_allowed


def test_read_permissions_exclude_pending() -> None:
    assert is_allowed("caregiver", "GET", "/api/status") is True
    assert is_allowed("doctor", "GET", "/api/timeline") is True
    assert is_allowed("admin", "GET", "/api/feedback/latest") is True
    assert is_allowed("pending", "GET", "/api/status") is False


def test_event_acknowledgement_is_caregiver_or_admin_only() -> None:
    assert is_allowed("caregiver", "POST", "/api/events/4/ack") is True
    assert is_allowed("admin", "POST", "/api/events/4/ack") is True
    assert is_allowed("doctor", "POST", "/api/events/4/ack") is False


def test_unknown_routes_and_methods_are_denied_by_default() -> None:
    assert is_allowed("admin", "DELETE", "/api/events/4") is False
    assert is_allowed("admin", "GET", "/private/debug") is False


def test_live_monitoring_role_matrix() -> None:
    assert can_open_websocket("caregiver") is True
    assert can_open_websocket("doctor") is True
    assert can_open_websocket("admin") is True
    assert can_open_websocket("pending") is False
