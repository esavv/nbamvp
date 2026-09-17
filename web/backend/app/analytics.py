"""Validated PostHog event collection for the web application."""

from functools import lru_cache
import logging
import os
from typing import Literal, Self
from uuid import UUID

from fastapi import APIRouter, Request, status
from posthog import Posthog
from pydantic import BaseModel, Field, model_validator


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

EventName = Literal[
    "page_viewed",
    "prediction_viewed",
    "season_changed",
    "week_changed",
    "results_toggled",
    "more_players_shown",
    "subscription_requested",
    "confirmation_page_viewed",
]
PropertyValue = str | int | bool
EVENT_PROPERTIES: dict[str, set[str]] = {
    "page_viewed": {"page", "layout"},
    "prediction_viewed": {"season", "week", "has_official_results", "layout"},
    "season_changed": {"from_season", "to_season", "layout"},
    "week_changed": {"season", "from_week", "to_week", "layout"},
    "results_toggled": {"season", "week", "from", "to", "layout"},
    "more_players_shown": {"season", "week", "from", "to", "layout"},
    "subscription_requested": {"layout"},
    "confirmation_page_viewed": {"layout"},
}


class AnalyticsEvent(BaseModel):
    distinct_id: UUID
    event: EventName
    properties: dict[str, PropertyValue] = Field(max_length=10)

    @model_validator(mode="after")
    def validate_properties(self) -> Self:
        expected = EVENT_PROPERTIES[self.event]
        if set(self.properties) != expected:
            raise ValueError(f"Properties for {self.event} must be: {', '.join(sorted(expected))}")
        if self.properties.get("layout") not in {"mobile", "desktop"}:
            raise ValueError("Layout must be mobile or desktop")
        if any(isinstance(value, str) and len(value) > 100 for value in self.properties.values()):
            raise ValueError("Analytics property values must not exceed 100 characters")
        return self


@lru_cache(maxsize=1)
def posthog_client() -> Posthog | None:
    api_key = os.getenv("POSTHOG_API_KEY")
    if not api_key:
        logger.warning("POSTHOG_API_KEY is not set; analytics are disabled")
        return None

    try:
        client = Posthog(api_key, host=os.getenv("POSTHOG_HOST", "https://us.i.posthog.com"))
    except Exception:
        logger.exception("Unable to initialize PostHog analytics")
        return None
    logger.info("PostHog analytics enabled")
    return client


def capture_event(event: str, distinct_id: str, properties: dict[str, PropertyValue] | None = None) -> None:
    client = posthog_client()
    if client is None:
        return

    try:
        client.capture(
            distinct_id=distinct_id,
            event=event,
            properties={**(properties or {}), "$process_person_profile": False},
        )
    except Exception:
        logger.exception("Unable to capture PostHog event %s", event)


def shutdown_analytics() -> None:
    if posthog_client.cache_info().currsize == 0:
        return
    client = posthog_client()
    if client is not None:
        try:
            client.shutdown()
        except Exception:
            logger.exception("Unable to shut down PostHog analytics")


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def collect_event(payload: AnalyticsEvent, request: Request) -> None:
    properties = dict(payload.properties)
    user_agent = request.headers.get("user-agent")
    if user_agent:
        properties["$user_agent"] = user_agent[:512]
    capture_event(payload.event, str(payload.distinct_id), properties)
