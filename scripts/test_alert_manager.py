import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )

from dashboard.alert_manager import ClassroomAlertManager


def main():

    manager = ClassroomAlertManager()

    test_state = {
        "timestamp": "2026-09-21 18:30:00",
        "tracked_persons": 2,
        "present_students": 1,
        "students": [
            {
                "track_id": 1,
                "student_id": "24AD095",
                "recognized": True,
                "similarity": 0.82,
                "attention": "NOT ATTENTIVE"
            }
        ]
    }

    alerts = manager.process_state(
        test_state
    )

    print()
    print("=" * 60)
    print("STEP 14 - ALERT MANAGER TEST")
    print("=" * 60)
    print()

    if alerts:

        for alert in alerts:

            print("Alert generated:")
            print(
                f"Alert ID : "
                f"{alert['alert_id']}"
            )

            print(
                f"Student  : "
                f"{alert['student_id']}"
            )

            print(
                f"Type     : "
                f"{alert['alert_type']}"
            )

            print(
                f"Message  : "
                f"{alert['message']}"
            )

            print(
                f"Status   : "
                f"{alert['status']}"
            )

    else:

        print(
            "No new alert generated."
        )

    print()

    print(
        "Alert statistics:"
    )

    print(
        manager.get_statistics()
    )

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()






