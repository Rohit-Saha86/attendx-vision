import cv2
import os


# ==========================================
# 1. Load Face Detector
# ==========================================

cascade_path = "haarcascade_frontalface_default.xml"

print("Cascade file:", cascade_path)

face_detector = cv2.CascadeClassifier(cascade_path)

if face_detector.empty():
    print("ERROR: Face detector could not be loaded.")
    exit()

print("Face detector loaded successfully.")


# ==========================================
# 2. Open Webcam
# ==========================================

camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open webcam.")
    exit()

print("Webcam started.")
print("Press Q to close the webcam.")


# ==========================================
# 3. Start Face Detection
# ==========================================

while True:

    success, frame = camera.read()

    if not success:
        print("ERROR: Could not read webcam.")
        break

    # Convert webcam image to grayscale
    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )

    # Detect faces
    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(100, 100)
    )

    # Draw rectangle around detected faces
    for (x, y, w, h) in faces:

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (255, 0, 0),
            2
        )

        cv2.putText(
            frame,
            "Face Detected",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 0, 0),
            2
        )

    # Show number of detected faces
    cv2.putText(
        frame,
        f"Faces: {len(faces)}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    # Display webcam
    cv2.imshow(
        "Face Detection - Press Q to Exit",
        frame
    )

    # Press Q to exit
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# 4. Close Webcam
# ==========================================

camera.release()
cv2.destroyAllWindows()

print("Webcam closed.")