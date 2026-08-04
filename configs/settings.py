from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_NAME = os.getenv("PROJECT_NAME")

PROJECT_VERSION = os.getenv("PROJECT_VERSION")

API_VERSION = os.getenv("API_VERSION")

HOST = os.getenv("HOST")

PORT = int(os.getenv("PORT"))

DEBUG = os.getenv("DEBUG") == "True"

DATABASE_URL = os.getenv("DATABASE_URL")

CAMERA_SOURCE = int(os.getenv("CAMERA_SOURCE"))

ATTENDANCE_THRESHOLD = float(os.getenv("ATTENDANCE_THRESHOLD"))

ATTENTION_THRESHOLD = float(os.getenv("ATTENTION_THRESHOLD"))