from ai.database.classroom_database import ClassroomDatabase


TEST_SESSION_ID = "TEST_ATTENTION_001"
TEST_STUDENT_ID = "24AD095"
TEST_TRACK_ID = 1


database = ClassroomDatabase()

print("============================================================")
print("STEP 17.8 - ATTENTION DATABASE TEST")
print("============================================================")

record = database.record_attention(
    session_id=TEST_SESSION_ID,
    student_id=TEST_STUDENT_ID,
    track_id=TEST_TRACK_ID,
    attention_state="ATTENTIVE",
    confidence=0.82,
)

print("")
print("Attention record created:")
print(f"ID              : {record.id}")
print(f"Session         : {record.session_id}")
print(f"Student         : {record.student_id}")
print(f"Track ID        : {record.track_id}")
print(f"Attention State : {record.attention_state}")
print(f"Confidence      : {record.confidence}")

print("")
print("============================================================")
print("ATTENTION DATABASE TEST PASSED")
print("============================================================")
