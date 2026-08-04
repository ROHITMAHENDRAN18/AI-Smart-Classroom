import cv2


def main():
    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        print("Failed to open webcam.")
        return

    print("Webcam started successfully.")
    print("Press Q to quit.")

    while True:
        success, frame = camera.read()

        if not success:
            print("Failed to read frame.")
            break

        cv2.imshow("AI Smart Classroom - Webcam", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
