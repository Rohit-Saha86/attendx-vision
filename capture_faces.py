import cv2
import os


DATASET_PATH = "dataset"
CASCADE_PATH = "haarcascade_frontalface_default.xml"

TOTAL_IMAGES = 30


student_id = input(
    "Enter Student ID: "
).strip()


if not student_id:

    print("Student ID cannot be empty.")
    exit()


os.makedirs(
    DATASET_PATH,
    exist_ok=True
)


face_detector = cv2.CascadeClassifier(
    CASCADE_PATH
)


if face_detector.empty():

    print("ERROR: Could not load face detector.")
    exit()


camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not camera.isOpened():

    print("ERROR: Could not open webcam.")
    exit()


print()
print("======================================")
print("Face Dataset Capture")
print("======================================")
print("Look at the camera.")
print(f"Capturing {TOTAL_IMAGES} images.")
print("Press Q to cancel.")
print()


count = 0


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

        count += 1


        filename = os.path.join(
            DATASET_PATH,
            f"User.{student_id}.{count}.jpg"
        )


        cv2.imwrite(
            filename,
            gray[y:y + h, x:x + w]
        )


        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            (255, 0, 0),
            2
        )


        cv2.putText(
            frame,
            f"Images: {count}/{TOTAL_IMAGES}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2
        )


        if count >= TOTAL_IMAGES:

            break


    cv2.imshow(
        "Capture Faces - Press Q to Exit",
        frame
    )


    if count >= TOTAL_IMAGES:

        break


    if cv2.waitKey(1) & 0xFF == ord("q"):

        break


camera.release()

cv2.destroyAllWindows()


print()

if count >= TOTAL_IMAGES:

    print(
        f"{TOTAL_IMAGES} face images captured successfully!"
    )

else:

    print(
        f"Capture stopped. {count} images saved."
    )