import os
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.dialects.postgresql import insert

from app import db
from app.models.api_usage import APIUsage


class UsageLimitExceeded(Exception):
    """Raised when a provider's daily request limit is reached."""


def reserve_api_request(provider="google_places", daily_limit=200):
    """Atomically reserve one API request for the current local date."""
    if daily_limit < 1:
        raise ValueError("daily_limit must be at least 1")

    timezone_name = os.getenv("LARVA_TIMEZONE", "Asia/Kolkata")
    usage_date = datetime.now(ZoneInfo(timezone_name)).date()

    statement = (
        insert(APIUsage)
        .values(
            provider=provider,
            usage_date=usage_date,
            request_count=1,
        )
        .on_conflict_do_update(
            index_elements=["provider", "usage_date"],
            set_={
                "request_count": APIUsage.request_count + 1,
                "updated_at": db.func.now(),
            },
            where=APIUsage.request_count < daily_limit,
        )
        .returning(APIUsage.request_count)
    )

    try:
        result = db.session.execute(statement)
        request_count = result.scalar_one_or_none()

        if request_count is None:
            db.session.rollback()
            raise UsageLimitExceeded(
                f"Daily API request limit reached for {provider} "
                f"({daily_limit} requests)."
            )

        db.session.commit()
        return request_count

    except UsageLimitExceeded:
        raise
    except Exception:
        db.session.rollback()
        raise
