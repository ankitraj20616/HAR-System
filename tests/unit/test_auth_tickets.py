import pytest

from services.auth_service.models import AuthenticatedUser
from services.auth_service.tickets import InvalidTicket, TicketManager


def user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="a70ea862-1bea-4dd3-9c33-16b2d24f07ce",
        email="caregiver@example.com",
        role="caregiver",
        session_id="282c9a21-1908-4616-b99f-80520c13cc4e",
    )


def test_ticket_is_target_bound_and_one_time() -> None:
    manager = TicketManager("x" * 32, 30)
    ticket = manager.issue(user(), "fusion")

    assert manager.consume(ticket, "fusion") == {
        "sub": user().user_id,
        "role": "caregiver",
    }
    with pytest.raises(InvalidTicket, match="already used"):
        manager.consume(ticket, "fusion")


def test_ticket_rejects_wrong_target_and_tampering() -> None:
    manager = TicketManager("x" * 32, 30)
    ticket = manager.issue(user(), "feedback")

    with pytest.raises(InvalidTicket, match="wrong target"):
        manager.consume(ticket, "fusion")
    with pytest.raises(InvalidTicket, match="signature"):
        manager.consume(ticket[:-1] + ("A" if ticket[-1] != "A" else "B"), "feedback")


def test_ticket_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = TicketManager("x" * 32, 5)
    monkeypatch.setattr("services.auth_service.tickets.time.time", lambda: 100)
    ticket = manager.issue(user(), "fusion")
    monkeypatch.setattr("services.auth_service.tickets.time.time", lambda: 106)

    with pytest.raises(InvalidTicket, match="expired"):
        manager.consume(ticket, "fusion")
