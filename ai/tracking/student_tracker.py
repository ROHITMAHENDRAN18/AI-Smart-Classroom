import time


class StudentTracker:

    def __init__(self):

        print("=" * 60)
        print("Loading Student Tracking Manager...")
        print("=" * 60)

        # --------------------------------------------------
        # Track ID -> Student Information
        # --------------------------------------------------

        self.track_to_student = {}

        # --------------------------------------------------
        # Student ID -> Track ID
        # --------------------------------------------------

        self.student_to_track = {}

        # --------------------------------------------------
        # Last time each track was seen
        # --------------------------------------------------

        self.last_seen = {}

        # --------------------------------------------------
        # Student attendance state
        # --------------------------------------------------

        self.student_status = {}

        print("Student Tracking Manager Loaded Successfully.")
        print("=" * 60)

    # ======================================================
    # ASSOCIATE STUDENT WITH TRACK
    # ======================================================

    def associate(self, track_id, student_id, similarity):

        current_time = time.time()

        # ----------------------------------------------
        # Convert values to standard types
        # ----------------------------------------------

        track_id = int(track_id)

        if student_id is not None:
            student_id = str(student_id)

        # ----------------------------------------------
        # Update last seen time
        # ----------------------------------------------

        self.last_seen[track_id] = current_time

        # ----------------------------------------------
        # Unknown student
        # ----------------------------------------------

        if student_id is None:
            return

        # ----------------------------------------------
        # Store Track -> Student
        # ----------------------------------------------

        self.track_to_student[track_id] = {
            "student_id": student_id,
            "similarity": float(similarity),
            "last_seen": current_time
        }

        # ----------------------------------------------
        # Store Student -> Track
        # ----------------------------------------------

        self.student_to_track[student_id] = track_id

        # ----------------------------------------------
        # Mark as present
        # ----------------------------------------------

        self.student_status[student_id] = "Present"

    # ======================================================
    # UPDATE TRACK WITHOUT NEW FACE RECOGNITION
    # ======================================================

    def update_track(self, track_id):

        track_id = int(track_id)

        current_time = time.time()

        self.last_seen[track_id] = current_time

        # ----------------------------------------------
        # If this track already belongs to a student
        # ----------------------------------------------

        if track_id in self.track_to_student:

            self.track_to_student[track_id]["last_seen"] = current_time

            student_id = self.track_to_student[track_id]["student_id"]

            self.student_status[student_id] = "Present"

            return student_id

        return None

    # ======================================================
    # GET STUDENT FROM TRACK
    # ======================================================

    def get_student(self, track_id):

        track_id = int(track_id)

        if track_id not in self.track_to_student:
            return None

        return self.track_to_student[track_id]["student_id"]

    # ======================================================
    # GET TRACK FROM STUDENT
    # ======================================================

    def get_track(self, student_id):

        student_id = str(student_id)

        return self.student_to_track.get(student_id)

    # ======================================================
    # GET SIMILARITY
    # ======================================================

    def get_similarity(self, track_id):

        track_id = int(track_id)

        if track_id not in self.track_to_student:
            return 0.0

        return self.track_to_student[track_id]["similarity"]

    # ======================================================
    # GET STATUS
    # ======================================================

    def get_status(self, student_id):

        student_id = str(student_id)

        return self.student_status.get(
            student_id,
            "Unknown"
        )

    # ======================================================
    # REMOVE OLD TRACKS
    # ======================================================

    def remove_lost_tracks(self, max_missing_seconds=2.0):

        current_time = time.time()

        lost_tracks = []

        for track_id, last_time in self.last_seen.items():

            if current_time - last_time > max_missing_seconds:

                lost_tracks.append(track_id)

        # ----------------------------------------------
        # Remove lost tracks
        # ----------------------------------------------

        for track_id in lost_tracks:

            student_data = self.track_to_student.pop(
                track_id,
                None
            )

            self.last_seen.pop(
                track_id,
                None
            )

            if student_data:

                student_id = student_data["student_id"]

                # Only remove reverse mapping if
                # it still points to this track
                if self.student_to_track.get(student_id) == track_id:

                    self.student_to_track.pop(
                        student_id,
                        None
                    )

    # ======================================================
    # GET ALL CURRENTLY TRACKED STUDENTS
    # ======================================================

    def get_tracked_students(self):

        result = []

        for track_id, data in self.track_to_student.items():

            result.append({
                "track_id": track_id,
                "student_id": data["student_id"],
                "similarity": data["similarity"],
                "last_seen": data["last_seen"],
                "status": self.student_status.get(
                    data["student_id"],
                    "Unknown"
                )
            })

        return result

    # ======================================================
    # GET NUMBER OF TRACKED STUDENTS
    # ======================================================

    def count(self):

        return len(self.track_to_student)