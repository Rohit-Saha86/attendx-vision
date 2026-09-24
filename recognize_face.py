import cv2
import os
import json

from database import get_students
from attendance import mark_attendance

# ==========================================
# SAVE RECOGNITION STATUS
# ==========================================

def save_recognition_status(
    status,
    student_id="",
    name="",
    attendance_marked=False
):
    data = {
        "status": status,
        "student_id": student_id,
        "name": name,
        "attendance_marked": attendance_marked
    }

    with open(
        "recognition_status.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=4
        )


# ==========================================
# FILE PATHS
# ==========================================

MODEL_PATH = "trainer/trainer.yml"
MAPPING_PATH = "trainer/student_mapping.txt"
CASCADE_PATH = "haarcascade_frontalface_default.xml"


# ==========================================
# CHECK FILES
# ==========================================

if not os.path.exists(MODEL_PATH):

    print("ERROR: trainer.yml not found.")
    print("Run train_model.py first.")
    exit()


if not os.path.exists(MAPPING_PATH):

    print("ERROR: student_mapping.txt not found.")
    print("Run train_model.py first.")
    exit()


if not os.path.exists(CASCADE_PATH):

    print("ERROR: Haar cascade file not found.")
    exit()


# ==========================================
# LOAD FACE DETECTOR
# ==========================================

face_detector = cv2.CascadeClassifier(
    CASCADE_PATH
)

if face_detector.empty():

    print("ERROR: Could not load face detector.")
    exit()


# ==========================================
# LOAD TRAINED MODEL
# ==========================================

recognizer = cv2.face.LBPHFaceRecognizer_create()

recognizer.read(MODEL_PATH)


# ==========================================
# LOAD LABEL MAPPING
# ==========================================

label_to_student = {}

with open(MAPPING_PATH, "r") as file:

    for line in file:

        line = line.strip()

        if not line:
            continue

        label, student_id = line.split(",", 1)

        label_to_student[int(label)] = student_id


# ==========================================
# LOAD STUDENT INFORMATION
# ==========================================

students = get_students()

student_data = {
    student["student_id"]: student
    for student in students
}


# ==========================================
# TRACK ATTENDANCE
# ==========================================

attendance_marked = set()


# ==========================================
# OPEN CAMERA
# ==========================================

camera = cv2.VideoCapture(
    0,
    cv2.CAP_DSHOW
)
if not camera.isOpened():

    print("ERROR: Could not open webcam.")
    exit()

save_recognition_status("waiting")
print()
print("======================================")
print("Face Recognition Attendance System")
print("======================================")
print("Camera started.")
print("Press Q to exit.")
print()


# ==========================================
# FACE RECOGNITION LOOP
# ==========================================

while True:

    success, frame = camera.read()

    if not success:

        print("ERROR: Could not read webcam.")
        break


    gray = cv2.cvtColor(
        frame,
        cv2.COLOR_BGR2GRAY
    )


    faces = face_detector.detectMultiScale(
        gray,
        scaleFactor=1.3,
        minNeighbors=5,
        minSize=(100, 100)
    )


    for (x, y, w, h) in faces:

        face_image = gray[
            y:y + h,
            x:x + w
        ]


        label, confidence = recognizer.predict(
            face_image
        )


        # LBPH confidence is a distance,
        # so lower values are better.
        display_score = max(
            0,
            min(
                100,
                round(100 - confidence)
            )
        )


        if (
            label in label_to_student
            and confidence < 80
        ):

            student_id = label_to_student[label]

            student = student_data.get(
                student_id
            )


            if student:

                name = student["name"]

                display_text = (
                    f"{name} ({student_id})"
                )


                confidence_text = (
                    f"Match Score: "
                    f"{display_score}%"
                )


                # Mark attendance only once
                # during this recognition session.
                if student_id not in attendance_marked:

                    attendance_result = mark_attendance(
                        student_id,
                        name
                    )

                    attendance_marked.add(
                        student_id
                    )

                    save_recognition_status(
                        "recognized",
                        student_id,
                        name,
                        attendance_result
                    )


            else:

                display_text = "Student Not Found"

                confidence_text = ""


        else:

            display_text = "Unknown Student"

            confidence_text = (
                f"Match Score: "
                f"{display_score}%"
            )


        # ==================================
        # DRAW FACE BOX
        # ==================================

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (255, 0, 0),
            2
        )


        # ==================================
        # DISPLAY NAME
        # ==================================

        cv2.putText(
            frame,
            display_text,
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )


        # ==================================
        # DISPLAY MATCH SCORE
        # ==================================

        if confidence_text:

            cv2.putText(
                frame,
                confidence_text,
                (x, y + h + 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
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

print()
print("Face recognition stopped.")