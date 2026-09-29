import cv2
import os
import json
import time
from datetime import datetime

from database import get_students
from attendance import mark_attendance


# ==========================================
# ABSOLUTE PROJECT PATHS
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "trainer", "trainer.yml")
MAPPING_PATH = os.path.join(BASE_DIR, "trainer", "student_mapping.txt")
CASCADE_PATH = os.path.join(BASE_DIR, "haarcascade_frontalface_default.xml")
STATUS_PATH = os.path.join(BASE_DIR, "trainer", "recognition_status.json")


def set_status(status, message="", student_id="", name=""):
    """Write recognition state so the Flask UI can show a popup."""
    data = {
        "status": status,
        "message": message,
        "student_id": student_id,
        "name": name,
        "time": datetime.now().isoformat(timespec="seconds")
    }

    try:
        os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
        temp_path = STATUS_PATH + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file)
        os.replace(temp_path, STATUS_PATH)
    except OSError:
        pass


# ==========================================
# CHECK FILES
# ==========================================
if not os.path.exists(MODEL_PATH):
    set_status("error", "Face model not found. Run train_model.py first.")
    print("ERROR: trainer.yml not found.")
    print("Run train_model.py first.")
    raise SystemExit(1)

if not os.path.exists(MAPPING_PATH):
    set_status("error", "Student mapping not found. Run train_model.py first.")
    print("ERROR: student_mapping.txt not found.")
    raise SystemExit(1)

if not os.path.exists(CASCADE_PATH):
    set_status("error", "Face detector file not found.")
    print("ERROR: Haar cascade file not found.")
    raise SystemExit(1)


# ==========================================
# LOAD FACE DETECTOR
# ==========================================
face_detector = cv2.CascadeClassifier(CASCADE_PATH)

if face_detector.empty():
    set_status("error", "Could not load the face detector.")
    print("ERROR: Could not load face detector.")
    raise SystemExit(1)


# ==========================================
# LOAD TRAINED MODEL
# ==========================================
try:
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(MODEL_PATH)
except Exception as error:
    set_status("error", f"Could not load face model: {error}")
    print(f"ERROR: Could not load face model: {error}")
    raise SystemExit(1)


# ==========================================
# LOAD LABEL MAPPING
# ==========================================
label_to_student = {}

try:
    with open(MAPPING_PATH, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            label, student_id = line.split(",", 1)
            label_to_student[int(label)] = student_id.strip()
except Exception as error:
    set_status("error", f"Could not read student mapping: {error}")
    print(f"ERROR: Could not read student mapping: {error}")
    raise SystemExit(1)


# ==========================================
# LOAD STUDENT INFORMATION
# ==========================================
try:
    students = get_students()
except Exception as error:
    set_status("error", f"Could not load students from database: {error}")
    print(f"ERROR: Could not load students from database: {error}")
    raise SystemExit(1)

student_data = {
    student["student_id"]: student
    for student in students
}


# ==========================================
# TRACK ATTENDANCE
# ==========================================
attendance_marked = set()
last_popup_time = 0
last_unknown_time = 0


# ==========================================
# OPEN CAMERA
# ==========================================
camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():
    # Fallback for systems where CAP_DSHOW is unavailable.
    camera.release()
    camera = cv2.VideoCapture(0)

if not camera.isOpened():
    set_status("error", "Could not open webcam. Check camera permissions.")
    print("ERROR: Could not open webcam.")
    raise SystemExit(1)

camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

set_status("scanning", "Camera started. Looking for a face...")

print()
print("======================================")
print("Face Recognition Attendance System")
print("======================================")
print("Camera started.")
print("Look directly at the camera.")
print("Press Q to exit.")
print()


# ==========================================
# FACE RECOGNITION LOOP
# ==========================================
while True:

    success, frame = camera.read()

    if not success:
        set_status("error", "Could not read webcam frame.")
        print("ERROR: Could not read webcam.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Improve contrast in different lighting conditions.
    gray = cv2.equalizeHist(gray)

    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(70, 70)
    )

    # Header shown inside the camera window.
    if len(faces) == 0:
        cv2.putText(
            frame,
            "Looking for face...",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 255),
            2
        )
        set_status("scanning", "No face detected. Look at the camera.")
    else:
        cv2.putText(
            frame,
            f"Face detected: {len(faces)}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

    for (x, y, w, h) in faces:

        face_image = gray[y:y + h, x:x + w]

        try:
            label, confidence = recognizer.predict(face_image)
        except cv2.error:
            label, confidence = -1, 999.0

        # LBPH uses distance: LOWER = better match.
        display_score = max(
            0,
            min(100, round(100 - confidence))
        )

        # 100 is deliberately used as a practical webcam threshold.
        # Lower the value if false matches ever occur.
        recognized = (
            label in label_to_student
            and confidence < 100
        )

        if recognized:
            student_id = label_to_student[label]
            student = student_data.get(student_id)

            if student:
                name = student["name"]

                if student_id not in attendance_marked:
                    try:
                        marked = mark_attendance(student_id, name)
                        attendance_marked.add(student_id)

                        if marked:
                            message = f"Attendance marked for {name}"
                        else:
                            message = f"{name} is already Present today"
                    except Exception as error:
                        message = f"Face matched, but attendance failed: {error}"
                else:
                    message = f"Welcome {name}"

                # Keep the browser popup from flashing repeatedly.
                now = time.time()
                if now - last_popup_time > 3:
                    set_status(
                        "recognized",
                        message,
                        student_id,
                        name
                    )
                    last_popup_time = now

                display_text = f"{name} - PRESENT"
                confidence_text = f"Match score: {display_score}%"

                box_color = (0, 255, 0)

            else:
                display_text = "Student not found"
                confidence_text = f"Match score: {display_score}%"
                box_color = (0, 165, 255)
                set_status(
                    "unknown",
                    "Face recognized, but student is not registered in the database."
                )

        else:
            display_text = "Unknown face"
            confidence_text = "Try better lighting / face the camera"
            box_color = (0, 0, 255)

            now = time.time()
            if now - last_unknown_time > 2:
                set_status("unknown", "Face detected, but no registered match was found.")
                last_unknown_time = now

        # ==================================
        # DRAW FACE BOX
        # ==================================
        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            box_color,
            2
        )

        # ==================================
        # DISPLAY NAME / STATUS
        # ==================================
        cv2.putText(
            frame,
            display_text,
            (x, max(25, y - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            box_color,
            2
        )

        cv2.putText(
            frame,
            confidence_text,
            (x, y + h + 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            box_color,
            2
        )

    cv2.imshow(
        "Face Recognition Attendance - Press Q to Exit",
        frame
    )

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break


# ==========================================
# CLOSE CAMERA
# ==========================================
camera.release()
cv2.destroyAllWindows()

set_status("idle", "Face recognition stopped.")

print()
print("Face recognition stopped.")
