import cv2
import os
import numpy as np


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, "dataset")
TRAINER_PATH = os.path.join(BASE_DIR, "trainer")


MODEL_PATH = os.path.join(
    TRAINER_PATH,
    "trainer.yml"
)

MAPPING_PATH = os.path.join(
    TRAINER_PATH,
    "student_mapping.txt"
)


os.makedirs(
    TRAINER_PATH,
    exist_ok=True
)


recognizer = cv2.face.LBPHFaceRecognizer_create()


image_paths = []


for filename in os.listdir(DATASET_PATH):

    if filename.lower().endswith(
        (".jpg", ".jpeg", ".png")
    ):

        image_paths.append(
            os.path.join(
                DATASET_PATH,
                filename
            )
        )


if not image_paths:

    print("ERROR: No training images found.")
    exit()


faces = []
student_ids = []


for image_path in image_paths:

    image = cv2.imread(
        image_path,
        cv2.IMREAD_GRAYSCALE
    )


    if image is None:

        print(
            f"Could not read: {image_path}"
        )

        continue


    filename = os.path.basename(
        image_path
    )


    parts = filename.split(".")


    if len(parts) < 3:

        print(
            f"Skipping invalid file: {filename}"
        )

        continue


    student_id = parts[1]


    faces.append(image)

    student_ids.append(student_id)


if not faces:

    print("ERROR: No valid training images found.")
    exit()


unique_student_ids = sorted(
    set(student_ids)
)


student_id_to_label = {
    student_id: index + 1
    for index, student_id
    in enumerate(unique_student_ids)
}


numeric_ids = [
    student_id_to_label[student_id]
    for student_id in student_ids
]


print(
    f"Found {len(faces)} training images."
)

print(
    f"Found {len(unique_student_ids)} students."
)

print()

print("Training model...")


recognizer.train(
    faces,
    np.array(numeric_ids)
)


recognizer.write(
    MODEL_PATH
)


with open(
    MAPPING_PATH,
    "w"
) as file:

    for student_id, label in (
        student_id_to_label.items()
    ):

        file.write(
            f"{label},{student_id}\n"
        )


print()
print("======================================")
print("Training completed successfully!")
print("======================================")

print(
    f"Model: {MODEL_PATH}"
)

print(
    f"Mapping: {MAPPING_PATH}"
)

print()

for student_id, label in (
    student_id_to_label.items()
):

    print(
        f"Label {label} -> {student_id}"
    )