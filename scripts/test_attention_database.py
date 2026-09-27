def main():
    from ai.database.classroom_database import ClassroomDatabase

    database = ClassroomDatabase()
    record = database.record_attention(
        session_id="TEST_ATTENTION_001",
        student_id="24AD095",
        track_id=1,
        attention_state="ATTENTIVE",
        confidence=0.82,
    )

    print("============================================================")
    print("STEP 17.8 - ATTENTION DATABASE TEST")
    print("============================================================")
    print("Attention record created:")
    print(f"ID              : {record.id}")
    print(f"Session         : {record.session_id}")
    print(f"Student         : {record.student_id}")
    print(f"Track ID        : {record.track_id}")
    print(f"Attention State : {record.attention_state}")
    print(f"Confidence      : {record.confidence}")
    print("============================================================")
    print("ATTENTION DATABASE TEST PASSED")
    print("============================================================")


if __name__ == "__main__":
    main()
