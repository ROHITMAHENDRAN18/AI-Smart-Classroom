import json
import os
from datetime import datetime


BASE_DIR = os.path.dirname(__file__)

ALERTS_DIR = os.path.join(
    BASE_DIR,
    "alerts"
)

ALERTS_FILE = os.path.join(
    ALERTS_DIR,
    "classroom_alerts.json"
)


class ClassroomAlertManager:

    def __init__(
        self,
        alerts_file=ALERTS_FILE
    ):

        self.alerts_file = alerts_file

        os.makedirs(
            os.path.dirname(
                self.alerts_file
            ),
            exist_ok=True
        )

        self.alerts = self._load_alerts()

        self.last_alert_time = {}

    def _load_alerts(self):

        if not os.path.exists(
            self.alerts_file
        ):

            return []

        try:

            with open(
                self.alerts_file,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(file)

            if isinstance(
                data,
                list
            ):

                return data

        except Exception as error:

            print(
                f"Alert file read error: {error}"
            )

        return []

    def _save_alerts(self):

        with open(
            self.alerts_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                self.alerts,
                file,
                indent=4
            )

    def _current_timestamp(self):

        return datetime.now().isoformat(
            timespec="seconds"
        )

    def create_alert(
        self,
        student_id,
        alert_type,
        message,
        track_id=None
    ):

        timestamp = self._current_timestamp()

        alert = {

            "alert_id":
                f"ALERT_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",

            "timestamp":
                timestamp,

            "student_id":
                student_id,

            "track_id":
                track_id,

            "alert_type":
                alert_type,

            "message":
                message,

            "status":
                "ACTIVE"

        }

        self.alerts.append(
            alert
        )

        self._save_alerts()

        return alert

    def create_attention_alert(
        self,
        student_id,
        track_id=None
    ):

        if not student_id:
            student_id = "UNKNOWN"

        alert_key = (
            f"{student_id}:NOT_ATTENTIVE"
        )

        now = datetime.now()

        previous_time = (
            self.last_alert_time.get(
                alert_key
            )
        )

        if previous_time:

            elapsed = (
                now - previous_time
            ).total_seconds()

            if elapsed < 30:

                return None

        self.last_alert_time[
            alert_key
        ] = now

        return self.create_alert(

            student_id=student_id,

            alert_type=
                "NOT_ATTENTIVE",

            message=
                f"Student {student_id} "
                f"is currently not attentive.",

            track_id=track_id
        )

    def process_state(
        self,
        state
    ):

        if not isinstance(
            state,
            dict
        ):

            return []

        students = state.get(
            "students",
            []
        )

        if not isinstance(
            students,
            list
        ):

            return []

        generated_alerts = []

        for student in students:

            if not isinstance(
                student,
                dict
            ):

                continue

            attention = str(
                student.get(
                    "attention",
                    "UNKNOWN"
                )
            ).upper()

            if attention != "NOT ATTENTIVE":
                continue

            student_id = (
                student.get(
                    "student_id"
                )
            )

            track_id = (
                student.get(
                    "track_id"
                )
            )

            alert = self.create_attention_alert(

                student_id=student_id,

                track_id=track_id
            )

            if alert:

                generated_alerts.append(
                    alert
                )

        return generated_alerts

    def get_alerts(
        self,
        limit=50
    ):

        return self.alerts[
            -limit:
        ][::-1]

    def get_active_alerts(self):

        return [
            alert
            for alert in self.alerts
            if alert.get(
                "status"
            ) == "ACTIVE"
        ]

    def acknowledge_alert(
        self,
        alert_id
    ):

        for alert in self.alerts:

            if alert.get(
                "alert_id"
            ) == alert_id:

                alert["status"] = (
                    "ACKNOWLEDGED"
                )

                alert["acknowledged_at"] = (
                    self._current_timestamp()
                )

                self._save_alerts()

                return alert

        return None

    def clear_alert(
        self,
        alert_id
    ):

        for alert in self.alerts:

            if alert.get(
                "alert_id"
            ) == alert_id:

                alert["status"] = (
                    "CLEARED"
                )

                alert["cleared_at"] = (
                    self._current_timestamp()
                )

                self._save_alerts()

                return alert

        return None

    def get_statistics(self):

        total = len(
            self.alerts
        )

        active = len(
            [
                alert
                for alert in self.alerts
                if alert.get(
                    "status"
                ) == "ACTIVE"
            ]
        )

        acknowledged = len(
            [
                alert
                for alert in self.alerts
                if alert.get(
                    "status"
                ) == "ACKNOWLEDGED"
            ]
        )

        cleared = len(
            [
                alert
                for alert in self.alerts
                if alert.get(
                    "status"
                ) == "CLEARED"
            ]
        )

        return {

            "total":
                total,

            "active":
                active,

            "acknowledged":
                acknowledged,

            "cleared":
                cleared

        }