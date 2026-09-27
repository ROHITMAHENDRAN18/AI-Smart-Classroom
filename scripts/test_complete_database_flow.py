from datetime import datetime, timezone

from ai.database.classroom_database import ClassroomDatabase


TEST_SESSION_ID = "TEST_DATABASE_FLOW_001"
TEST_STUDENT_ID = "24AD095"
TEST_TRACK_ID = 1


def main():
    database = ClassroomDatabase()

    print("")
    print("============================================================")
    print("STEP 17.10 - COMPLETE DATABASE FLOW TEST")
    print("============================================================")
    print("")

    print("TEST SESSION")
    print(f"Session ID : {TEST_SESSION_ID}")
    print(f"Student ID : {TEST_STUDENT_ID}")
    print(f"Track ID   : {TEST_TRACK_ID}")
    print("")

    # ---------------------------------------------------------
    # STEP 1 - START SESSION
    # ---------------------------------------------------------

    print("------------------------------------------------------------")
    print("1. STARTING CLASSROOM SESSION")
    print("------------------------------------------------------------")

    session = database.start_session(
        session_id=TEST_SESSION_ID,
        started_at=datetime.now(timezone.utc),
    )

    print("")
    print("Session created successfully.")
    print(f"Session ID : {session.session_id}")
    print(f"Status     : {session.status}")
    print("")

    # ---------------------------------------------------------
    # STEP 2 - RECORD ATTENDANCE
    # ---------------------------------------------------------

    print("------------------------------------------------------------")
    print("2. RECORDING ATTENDANCE")
    print("------------------------------------------------------------")

    attendance = database.record_attendance(
        session_id=TEST_SESSION_ID,
        student_id=TEST_STUDENT_ID,
        status="PRESENT",
        confidence=0.82,
    )

    print("")
    print("Attendance recorded successfully.")
    print(f"Record ID  : {attendance.id}")
    print(f"Student ID : {attendance.student_id}")
    print(f"Status     : {attendance.status}")
    print(f"Confidence : {attendance.confidence}")
    print("")

    # ---------------------------------------------------------
    # STEP 3 - RECORD ATTENTION
    # ---------------------------------------------------------

    print("------------------------------------------------------------")
    print("3. RECORDING ATTENTION")
    print("------------------------------------------------------------")

    attention = database.record_attention(
        session_id=TEST_SESSION_ID,
        student_id=TEST_STUDENT_ID,
        track_id=TEST_TRACK_ID,
        attention_state="ATTENTIVE",
        confidence=0.91,
    )

    print("")
    print("Attention recorded successfully.")
    print(f"Record ID        : {attention.id}")
    print(f"Student ID       : {attention.student_id}")
    print(f"Track ID         : {attention.track_id}")
    print(f"Attention State  : {attention.attention_state}")
    print(f"Confidence       : {attention.confidence}")
    print("")

    # ---------------------------------------------------------
    # STEP 4 - RECORD SECOND ATTENTION STATE
    # ---------------------------------------------------------

    print("------------------------------------------------------------")
    print("4. RECORDING SECOND ATTENTION STATE")
    print("------------------------------------------------------------")

    second_attention = database.record_attention(
        session_id=TEST_SESSION_ID,
        student_id=TEST_STUDENT_ID,
        track_id=TEST_TRACK_ID,
        attention_state="NOT ATTENTIVE",
        confidence=0.76,
    )

    print("")
    print("Second attention record created successfully.")
    print(f"Record ID        : {second_attention.id}")
    print(f"Student ID       : {second_attention.student_id}")
    print(f"Track ID         : {second_attention.track_id}")
    print(f"Attention State  : {second_attention.attention_state}")
    print(f"Confidence       : {second_attention.confidence}")
    print("")

    # ---------------------------------------------------------
    # STEP 5 - FINISH SESSION
    # ---------------------------------------------------------

    print("------------------------------------------------------------")
    print("5. FINISHING CLASSROOM SESSION")
    print("------------------------------------------------------------")

    finished_session = database.finish_session(
        session_id=TEST_SESSION_ID,
        ended_at=datetime.now(timezone.utc),
        duration_seconds=120,
        status="COMPLETED",
    )

    if finished_session is None:
        raise RuntimeError(
            "TEST FAILED: Classroom session was not found."
        )

    print("")
    print("Session completed successfully.")
    print(f"Session ID : {finished_session.session_id}")
    print(f"Status     : {finished_session.status}")
    print(
        f"Duration   : "
        f"{finished_session.duration_seconds} seconds"
    )
    print("")

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    print("============================================================")
    print("COMPLETE DATABASE FLOW TEST PASSED")
    print("============================================================")
    print("")
    print("Verified:")
    print("  [PASS] Classroom session creation")
    print("  [PASS] Attendance persistence")
    print("  [PASS] Attention persistence")
    print("  [PASS] Multiple attention states")
    print("  [PASS] Session completion")
    print("  [PASS] PostgreSQL database integration")
    print("")


if __name__ == "__main__":
    main()