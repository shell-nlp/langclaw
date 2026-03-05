"""LangChain tools for RentAgent VN.

- ``search_rentals``    — primary tool, uses TinyFish via scrape workflow
- ``contact_landlord``  — stub, returns contact info for manual outreach
- ``research_area``     — uses built-in web_search + web_fetch
"""

from __future__ import annotations

import os
from typing import Any

from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from loguru import logger

from examples.rentagent_vn.prompts import DEFAULT_PLATFORM_URLS
from examples.rentagent_vn.scrape_workflow import BackgroundScrapeRunner

# ---------------------------------------------------------------------------
# Background runner (set by app.py on startup)
# ---------------------------------------------------------------------------

_bg_runner: BackgroundScrapeRunner | None = None


def set_background_runner(runner: BackgroundScrapeRunner) -> None:
    """Inject the background scrape runner (called from ``app.py``)."""
    global _bg_runner
    _bg_runner = runner


def _get_rental_urls() -> list[str]:
    """Read rental URLs from env or fall back to defaults.

    In production the frontend injects URLs via ToolRuntime state.  For
    the terminal MVP we also support the ``RENTAGENT_URLS`` env var
    (comma-separated).
    """
    env_urls = os.environ.get("RENTAGENT_URLS", "")
    if env_urls:
        return [u.strip() for u in env_urls.split(",") if u.strip()]
    return list(DEFAULT_PLATFORM_URLS)


@tool
async def search_rentals(
    query: str,
    user_preference: str | None = None,
    *,
    runtime: ToolRuntime,
) -> dict[str, Any]:
    """Search rental listings across configured platforms.

    This tool starts a background scrape job and returns immediately.
    Results are delivered directly to the user's channel when ready
    (typically 3–8 minutes depending on the number of platforms).

    Args:
        query: What to search for, written in natural language in the language of the user. Describe
            the property the user wants: area, bedrooms, budget, special
            requirements. Examples:
            - "2-bedroom apartment in District 7, under 15 million VND/month"
            - "phong tro gan Dai hoc Bach Khoa, duoi 5 trieu"
            - "pet-friendly studio in Binh Thanh with balcony"
        user_preference: Optional context about what the user actually
            prefers based on the conversation so far. Pass inferred
            patterns that go beyond the explicit query, e.g.
            "prefers high floors, dislikes ground floor units, wants
            quiet neighbourhood".
    """
    if _bg_runner is None:
        return {"error": "Background scrape runner not initialized"}

    urls = runtime.state.get("rental_urls") or _get_rental_urls()
    logger.info("search_rentals called — {} URLs, query={!r}", len(urls), query[:80])

    configurable = runtime.config.get("configurable", {})
    channel_context: dict[str, Any] = dict(configurable.get("channel_context", {}))
    # Include thread_id so delivery can target the same LangGraph thread/session
    if "thread_id" not in channel_context and "thread_id" in configurable:
        channel_context["thread_id"] = configurable["thread_id"]

    job_id = await _bg_runner.start(
        urls=urls,
        query=query,
        user_preference=user_preference,
        channel_context=channel_context,
    )
    logger.info("search_rentals job_id: {}", job_id)

    return {
        "status": "started",
        "message": (
            "Notify the user that we are "
            f"searching {len(urls)} platform(s) in the background. "
            "Results will be delivered to this chat when ready."
        ),
        "urls_scanned": len(urls),
    }


@tool
async def contact_landlord(
    landlord_name: str,
    landlord_phone: str,
    message: str,
) -> dict[str, Any]:
    """Send a message to a landlord about a rental listing via Zalo.

    If Zalo is connected, sends the message directly. Otherwise, returns
    the landlord's contact info so the user can reach out manually.

    Args:
        landlord_name: Name of the landlord/poster.
        landlord_phone: Phone number of the landlord.
        message: The message to send to the landlord, e.g. asking about
            availability, price negotiation, or scheduling a viewing.
    """
    import httpx

    logger.info("contact_landlord called for {}", landlord_name)

    zalo_api_url = os.environ.get("ZALO_SERVICE_URL", "http://localhost:8001")

    # Check Zalo connection status
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            status_resp = await client.get(f"{zalo_api_url}/auth/status")
            if status_resp.status_code != 200:
                raise httpx.ConnectError("Service unavailable")
            status = status_resp.json()
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.info("Zalo service not available, returning manual contact info")
        return {
            "status": "zalo_unavailable",
            "suggestion": ("Zalo service is not running. Contact the landlord directly."),
            "landlord_name": landlord_name,
            "landlord_phone": landlord_phone,
            "message_draft": message,
            "channels": {
                "zalo": (f"https://zalo.me/{landlord_phone}" if landlord_phone else None),
                "phone": landlord_phone,
            },
        }

    if not status.get("connected"):
        logger.info("Zalo not connected, returning manual contact info")
        return {
            "status": "zalo_not_connected",
            "suggestion": (
                "Zalo is not connected. Ask the user to connect Zalo "
                "in settings, then contact the landlord directly."
            ),
            "landlord_name": landlord_name,
            "landlord_phone": landlord_phone,
            "message_draft": message,
            "channels": {
                "zalo": (f"https://zalo.me/{landlord_phone}" if landlord_phone else None),
                "phone": landlord_phone,
            },
        }

    # Zalo is connected — send the message
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            send_resp = await client.post(
                f"{zalo_api_url}/message/send",
                json={"phone": landlord_phone, "text": message},
            )
            if send_resp.status_code != 200:
                error_data = send_resp.json()
                return {
                    "status": "send_failed",
                    "error": error_data.get("error", "Unknown error"),
                    "landlord_name": landlord_name,
                    "landlord_phone": landlord_phone,
                    "message_draft": message,
                }

            result = send_resp.json()
            logger.info("Message sent to {} via Zalo", landlord_phone)
            return {
                "status": "sent",
                "message": (f"Message sent to {landlord_name} ({landlord_phone}) via Zalo."),
                "zalo_user_id": result.get("userId"),
                "landlord_name": landlord_name,
                "landlord_phone": landlord_phone,
            }
    except Exception as exc:
        logger.error("Failed to send Zalo message: {}", exc)
        return {
            "status": "send_failed",
            "error": str(exc),
            "suggestion": ("Failed to send via Zalo. Contact the landlord directly."),
            "landlord_name": landlord_name,
            "landlord_phone": landlord_phone,
            "message_draft": message,
            "channels": {
                "zalo": (f"https://zalo.me/{landlord_phone}" if landlord_phone else None),
                "phone": landlord_phone,
            },
        }


@tool
async def research_area(
    area_name: str,
    city: str = "Ho Chi Minh",
) -> dict[str, Any]:
    """Research a neighbourhood or district for rental suitability.

    Uses web search to gather information about safety, amenities,
    transport links, and reviews for a given area. Does NOT use TinyFish.

    Args:
        area_name: Name of the district or neighbourhood, e.g.
            "Quan 7", "Binh Thanh", "Thao Dien".
        city: City name. Defaults to "Ho Chi Minh".
    """
    logger.info("research_area called for {} in {}", area_name, city)

    try:
        from langclaw.agents.tools.web_search import make_web_search_tool
    except ImportError:
        return {"error": ("Web search tools not available. Install with: uv add langclaw[search]")}

    search_tool = make_web_search_tool("duckduckgo")

    queries = [
        f"{area_name} {city} Vietnam rental review",
        f"{area_name} {city} safety neighbourhood amenities",
    ]
    results: list[dict[str, Any]] = []
    for q in queries:
        try:
            res = await search_tool.ainvoke(q)
            results.append({"query": q, "results": res})
        except Exception as exc:
            results.append({"query": q, "error": str(exc)})

    return {
        "area": area_name,
        "city": city,
        "research": results,
    }
