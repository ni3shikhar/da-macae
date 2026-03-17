"""Shared utility functions: RAI validation, logging, helpers."""

from __future__ import annotations

import logging
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ── RAI (Responsible AI) Validation ───────────────────────────────────


_RAI_SYSTEM_PROMPT = """You are a content safety classifier. Your job is to
determine if the user's input contains harmful, hateful, racist, sexist,
violent, or otherwise unsafe content.

Respond with ONLY one word:
- TRUE if the content should be BLOCKED
- FALSE if the content is SAFE

Do not explain your reasoning."""


async def validate_rai(
    content: str,
    *,
    openai_client: Any | None = None,
    model: str = "gpt-4o",
) -> bool:
    """Return True if content passes RAI validation (is safe).

    Returns False if content should be blocked.
    """
    if not content or not content.strip():
        return True

    if openai_client is None:
        # If no client provided, default to safe (allow)
        logger.warning("rai_validation_skipped", reason="no_openai_client")
        return True

    try:
        response = await openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _RAI_SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            max_tokens=10,
            temperature=0.0,
        )
        result = response.choices[0].message.content.strip().upper()
        is_safe = result != "TRUE"
        if not is_safe:
            logger.warning("rai_content_blocked", content_preview=content[:100])
        return is_safe
    except Exception:
        logger.exception("rai_validation_error")
        # Fail open — allow content if RAI check errors
        return True


# ── Text Utilities ─────────────────────────────────────────────────────


def sanitize_name(name: str) -> str:
    """Sanitize a string to be used as an identifier."""
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip().lower())


def truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length, adding ellipsis if needed."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


# ── Logging Setup ──────────────────────────────────────────────────────


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output for production."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if log_level == "DEBUG"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
