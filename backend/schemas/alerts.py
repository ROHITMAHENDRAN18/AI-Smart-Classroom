from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    alert_id: str
    alert_type: str
    message: str
    severity: str | None
    timestamp: datetime
    session_id: str
    student_id: str
    track_id: int | None
