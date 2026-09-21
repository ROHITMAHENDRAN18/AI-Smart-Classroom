import cv2
import os
import threading


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FRAME_FILE = os.path.join(
    BASE_DIR,
    "camera_latest.jpg"
)


class CameraStream:

    def __init__(self):

        self.frame_file = FRAME_FILE

        self.lock = threading.Lock()

        os.makedirs(
            BASE_DIR,
            exist_ok=True
        )

    def update_frame(self, frame):

        if frame is None:
            return

        success, encoded = cv2.imencode(
            ".jpg",
            frame,
            [
                cv2.IMWRITE_JPEG_QUALITY,
                80
            ]
        )

        if not success:
            return

        temp_file = self.frame_file + ".tmp"

        try:

            with self.lock:

                with open(
                    temp_file,
                    "wb"
                ) as file:

                    file.write(
                        encoded.tobytes()
                    )

                os.replace(
                    temp_file,
                    self.frame_file
                )

        except Exception as error:

            print(
                f"CameraStream update error: {error}"
            )

            try:

                if os.path.exists(
                    temp_file
                ):

                    os.remove(
                        temp_file
                    )

            except Exception:
                pass

    def get_frame(self):

        return self.get_jpeg()

    def get_jpeg(self):

        try:

            with self.lock:

                if not os.path.exists(
                    self.frame_file
                ):

                    return None

                with open(
                    self.frame_file,
                    "rb"
                ) as file:

                    return file.read()

        except (
            FileNotFoundError,
            PermissionError,
            OSError
        ):

            return None

    def clear(self):

        try:

            with self.lock:

                if os.path.exists(
                    self.frame_file
                ):

                    os.remove(
                        self.frame_file
                    )

        except Exception as error:

            print(
                f"CameraStream clear error: {error}"
            )