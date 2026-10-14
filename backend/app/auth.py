from secrets import compare_digest
from typing import Annotated

from fastapi import Header, HTTPException

from app.config import get_settings


def get_requester(x_demo_token: Annotated[str | None, Header()] = None) -> str:
    expected = get_settings().demo_requester_token.get_secret_value()
    if not x_demo_token or not compare_digest(x_demo_token.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Valid demo requester token required")
    # Identity is chosen by the server, never accepted in the request body.
    return "demo-requester"


def get_approver(x_demo_approver_token: Annotated[str | None, Header()] = None) -> str:
    secret = get_settings().demo_approver_token
    if secret is None or not x_demo_approver_token:
        raise HTTPException(status_code=403, detail="Demo reviewer token required")
    if not compare_digest(x_demo_approver_token.encode(), secret.get_secret_value().encode()):
        raise HTTPException(status_code=403, detail="Demo reviewer token required")
    return "demo-reviewer"
