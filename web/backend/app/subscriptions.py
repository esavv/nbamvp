"""Double-opt-in newsletter subscription endpoints."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import time
from urllib.parse import quote
import hmac
import json
import logging
import os
import secrets
import sys

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src import ses_service  # noqa: E402


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://nba-mvp.com").rstrip("/")
TOKEN_LIFETIME_SECONDS = 48 * 60 * 60
RATE_LIMIT_SECONDS = 60 * 60
RATE_LIMIT_ATTEMPTS = 5
_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = Lock()


class SubscriptionRequest(BaseModel):
    email: str
    website: str = ""


class ConfirmationRequest(BaseModel):
    token: str


def _encode(value: bytes) -> str:
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_confirmation_token(email: str) -> str:
    payload = {
        "email": ses_service.normalize_email(email),
        "expires": int(time()) + TOKEN_LIFETIME_SECONDS,
        "nonce": secrets.token_urlsafe(8),
    }
    encoded = _encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        ses_service.get_subscription_secret().encode("utf-8"),
        encoded.encode("ascii"),
        sha256,
    ).digest()
    return f"{encoded}.{_encode(signature)}"


def verify_confirmation_token(token: str) -> str:
    try:
        encoded, provided_signature = token.split(".", 1)
        expected_signature = hmac.new(
            ses_service.get_subscription_secret().encode("utf-8"),
            encoded.encode("ascii"),
            sha256,
        ).digest()
        if not hmac.compare_digest(expected_signature, _decode(provided_signature)):
            raise ValueError("Invalid signature")
        payload = json.loads(_decode(encoded))
        if int(payload["expires"]) < int(time()):
            raise ValueError("Expired token")
        return ses_service.normalize_email(payload["email"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired confirmation link") from exc


def _rate_limited(key: str) -> bool:
    now = time()
    cutoff = now - RATE_LIMIT_SECONDS
    with _attempts_lock:
        recent = [attempt for attempt in _attempts[key] if attempt >= cutoff]
        _attempts[key] = recent
        if len(recent) >= RATE_LIMIT_ATTEMPTS:
            return True
        recent.append(now)
        return False


def _confirmation_html(confirmation_url: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <body style="margin:0;padding:24px;background:#f1f5f9;font-family:Arial,sans-serif;color:#0f172a;">
    <div style="max-width:560px;margin:0 auto;padding:28px;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;">
      <table role="presentation" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
        <tr>
          <td style="padding:0 10px 0 0;font-size:28px;line-height:1;vertical-align:middle;">🏀</td>
          <td style="font-size:24px;font-weight:700;line-height:1.2;vertical-align:middle;">Confirm your subscription</td>
        </tr>
      </table>
      <p style="margin:12px 0 22px;color:#64748b;line-height:1.6;">
        Confirm that you want to receive weekly NBA MVP predictions during the season.
      </p>
      <a href="{confirmation_url}" style="display:inline-block;padding:12px 18px;border-radius:9px;background:#ea580c;color:#ffffff;font-weight:700;text-decoration:none;">
        Confirm subscription
      </a>
      <p style="margin:22px 0 0;color:#94a3b8;font-size:12px;line-height:1.5;">
        If you did not request this email, you can ignore it. This link expires in 48 hours.
      </p>
    </div>
  </body>
</html>"""


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def request_subscription(payload: SubscriptionRequest, request: Request) -> dict[str, str]:
    response = {
        "message": "Check your inbox for a confirmation link. It may take a few minutes to arrive."
    }
    if payload.website:
        return response

    try:
        email = ses_service.normalize_email(payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Enter a valid email address.") from exc

    client_address = request.client.host if request.client else "unknown"
    if _rate_limited(f"ip:{client_address}") or _rate_limited(f"email:{email}"):
        return response

    try:
        token = create_confirmation_token(email)
        confirmation_url = f"{WEBAPP_URL}/?subscription_token={quote(token)}"
        ses_service.send_email(
            email,
            "Confirm your NBA MVP Predictions subscription",
            _confirmation_html(confirmation_url),
            f"Confirm your subscription: {confirmation_url}",
            tags={"message_type": "subscription-confirmation"},
        )
    except (BotoCoreError, ClientError):
        logger.exception("Unable to send subscription confirmation")
        raise HTTPException(
            status_code=503,
            detail="Subscriptions are temporarily unavailable. Please try again later.",
        )
    return response


@router.post("/confirm")
def confirm_subscription(payload: ConfirmationRequest) -> dict[str, str]:
    try:
        email = verify_confirmation_token(payload.token)
        ses_service.subscribe_contact(email, source="web-double-opt-in")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (BotoCoreError, ClientError):
        logger.exception("Unable to confirm newsletter subscription")
        raise HTTPException(
            status_code=503,
            detail="Confirmation is temporarily unavailable. Please try again later.",
        )
    return {"message": "You're subscribed! The next NBA MVP prediction will arrive by email."}
