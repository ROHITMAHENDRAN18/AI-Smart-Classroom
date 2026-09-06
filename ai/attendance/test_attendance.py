from ai.attendance.attendance_manager import AttendanceManager


print("=" * 60)
print("STEP 7 - ATTENDANCE MANAGER TEST")
print("=" * 60)


# ------------------------------------------------------------
# Create Attendance Manager
# ------------------------------------------------------------

attendance = AttendanceManager()


# ------------------------------------------------------------
# Show existing count
# ------------------------------------------------------------

print(
    f"Today's attendance count: "
    f"{attendance.get_today_count()}"
)


# ------------------------------------------------------------
# Test Student
# ------------------------------------------------------------

student_id = "24AD095"


print()
print(
    f"Testing Student ID: {student_id}"
)


# ------------------------------------------------------------
# Mark attendance
# ------------------------------------------------------------

marked = attendance.mark_attendance(
    student_id
)


if marked:

    print(
        f"SUCCESS: {student_id} marked Present."
    )

else:

    print(
        f"INFO: {student_id} was already marked today."
    )


# ------------------------------------------------------------
# Final count
# ------------------------------------------------------------

print()
print(
    f"Today's attendance count: "
    f"{attendance.get_today_count()}"
)

print("=" * 60)
print("STEP 7 ATTENDANCE MANAGER TEST COMPLETE")
print("=" * 60)