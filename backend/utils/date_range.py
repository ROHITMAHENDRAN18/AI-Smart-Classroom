from datetime import date, datetime, time, timedelta, timezone

from fastapi import HTTPException, status


def get_utc_date_range(
    from_date: date | None,
    to_date: date | None,
) -> tuple[datetime | None, datetime | None]:
    if from_date is not None and to_date is not None:
        if from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="from_date must not be after to_date.",
            )
        if (to_date - from_date).days > 365:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Date ranges cannot exceed 366 days.",
            )

    start_at = (
        datetime.combine(from_date, time.min, tzinfo=timezone.utc)
        if from_date is not None
        else None
    )
    end_at = (
        datetime.combine(
            to_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )
        if to_date is not None
        else None
    )
    return start_at, end_at
