import cv2
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")
CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")

TOTAL_IMAGES = 30

student_id = input("Enter Student ID: ").strip()

if not student_id:
    print("Student ID cannot be empty.")
    raise SystemExit(1)

os.makedirs(DATASET_PATH, exist_ok=True)

face_detector = cv2.CascadeClassifier(CASCADE_PATH)

if face_detector.empty():
    print("ERROR: Could not load face detector.")
    raise SystemExit(1)

camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not camera.isOpened():
    camera.release()
    camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("ERROR: Could not open webcam.")
    raise SystemExit(1)

print("\n======================================")
print("Face Dataset Capture")
print("======================================")
print("Look directly at the camera.")
print(f"Capturing {TOTAL_IMAGES} good face images.")
print("Press Q to cancel.\n")

count = 0
last_saved = 0

while True:
    success, frame = camera.read()
    if not success:
        print("ERROR: Could not read webcam.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(70, 70)
    )

    if len(faces) == 0:
        cv2.putText(frame, "No face detected - look at camera",
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (0, 0, 255), 2)

    for (x, y, w, h) in faces[:1]:
        # Save at most one image every 0.12 seconds.
        now = time.time()
        if now - last_saved >= 0.12 and count < TOTAL_IMAGES:
            face_crop = gray[y:y+h, x:x+w]
            count += 1
            filename = os.path.join(
                DATASET_PATH,
                f"User.{student_id}.{count}.jpg"
            )
            cv2.imwrite(filename, face_crop)
            last_saved = now

        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(frame, f"Images: {count}/{TOTAL_IMAGES}",
                    (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 255, 0), 2)

    cv2.imshow("Capture Faces - Press Q to Exit", frame)

    if count >= TOTAL_IMAGES or (cv2.waitKey(1) & 0xFF == ord("q")):
        break

camera.release()
cv2.destroyAllWindows()

print()
if count >= TOTAL_IMAGES:
    print(f"{TOTAL_IMAGES} face images captured successfully!")
    print("IMPORTANT: Run train_model.py before recognition.")
else:
    print(f"Capture stopped. {count} images saved.")
