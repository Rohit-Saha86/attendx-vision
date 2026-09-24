# AttendX Vision

A local face recognition attendance system built with Python, Flask, OpenCV, MySQL, and a browser-based recognition interface.

AttendX Vision captures registered faces, trains a local face recognition model, verifies users through a webcam, and records attendance in a MySQL database. The web interface provides a futuristic biometric-style dashboard with real-time recognition feedback and liveness interaction.

## Features

* Admin login and protected application pages
* Student registration and management
* Webcam-based face capture
* Local face recognition using OpenCV LBPH
* MySQL-backed student and attendance records
* Automatic prevention of duplicate attendance for the same student on the same day
* Attendance dashboard and reports
* Attendance CSV export
* Attendance count and student attendance streak
* Animated face recognition interface
* Face mesh visualization in the browser
* Smile/blink liveness interaction
* Low-light detection and visual assistance
* Multi-scan mode
* Recent scan queue
* Flagged-attempt counter
* Local processing architecture with no cloud face-recognition service
* Automated tests with pytest
* GitHub Actions CI

## Tech Stack

| Technology             | Purpose                                        |
| ---------------------- | ---------------------------------------------- |
| Python                 | Backend and recognition logic                  |
| Flask                  | Web application                                |
| OpenCV                 | Face capture and recognition                   |
| OpenCV LBPH            | Local face recognition model                   |
| MySQL                  | Student and attendance database                |
| HTML5                  | Web interface                                  |
| CSS                    | UI styling and animations                      |
| JavaScript             | Recognition interface and browser interactions |
| MediaPipe Tasks Vision | Browser-side face landmark visualization       |
| pytest                 | Automated testing                              |
| GitHub Actions         | Continuous integration                         |

## Project Structure

```text
attendx-vision/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── static/
│   ├── css/
│   │   └── recognition.css
│   ├── js/
│   │   └── recognition.js
│   └── style.css
│
├── templates/
│   ├── attendance.html
│   ├── dashboard.html
│   ├── index.html
│   ├── login.html
│   ├── recognition.html
│   ├── register.html
│   ├── reports.html
│   └── students.html
│
├── tests/
│   └── test_app.py
│
├── app.py
├── attendance.py
├── auth.py
├── capture_faces.py
├── config.py
├── create_admin.py
├── dashboard.py
├── database.py
├── face_capture.py
├── haarcascade_frontalface_default.xml
├── recognize_face.py
├── train_model.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## How It Works

The system uses a local recognition pipeline:

```text
Student Registration
        ↓
Face Capture
        ↓
Training Images
        ↓
LBPH Model Training
        ↓
Webcam Recognition
        ↓
Student Identification
        ↓
Attendance Database
        ↓
Dashboard / Reports
```

The browser recognition page also provides visual face-landmark feedback and a liveness interaction before the backend recognition result is displayed.

## Requirements

Before running the project, install:

* Python 3.13+
* MySQL Server
* MySQL Workbench (optional)
* A working webcam
* Git

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Rohit-Saha86/attendx-vision.git
cd attendx-vision
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
FLASK_SECRET_KEY=your-random-secret-key
```

The `.env` file should remain local and must not be committed to Git.

### 5. Configure MySQL

Create the required database and tables:

```text
face_attendance
```

The application expects the student, attendance, and admin data used by the Flask/MySQL backend.

Configure the database connection according to your local MySQL setup.

## Running the Application

Start the Flask application:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

Log in through the admin login page.

## Face Registration Workflow

### Register a student

Use the registration page to add a student with:

* Student ID
* Name
* Email
* Department

### Capture face images

Run:

```powershell
python capture_faces.py
```

Enter the registered student ID when prompted.

The system captures face images from the webcam for training.

### Train the recognition model

Run:

```powershell
python train_model.py
```

The trained recognition model is stored locally.

### Start recognition

The application can launch the recognition process from the recognition interface.

The local Python recognizer uses the trained OpenCV model to identify registered students and update the recognition status used by the web interface.

## Testing

Run the automated test suite:

```powershell
pytest
```

Current test coverage includes:

* Login page loading
* Authentication protection for the home page
* Attendance module availability
* Registration validation

## Continuous Integration

GitHub Actions runs the test suite automatically on pushes and pull requests.

Workflow:

```text
.github/workflows/ci.yml
```

The CI pipeline installs project dependencies and runs:

```text
pytest
```

## Security Notes

The project keeps local secrets and biometric/training data out of version control.

The following are ignored by Git:

```text
.env
venv/
dataset/
trainer/
recognition_status.json
*.csv
```

Do not commit:

* Database passwords
* Flask secret keys
* Captured biometric images
* Local trained model files
* Other private credentials

## Recognition and Liveness

AttendX Vision combines backend face recognition with a browser-side liveness interaction.

The smile/blink interaction is intended as a basic liveness check and user interaction layer. It should not be considered a complete anti-spoofing or presentation-attack defense.

For high-security deployments, additional biometric security and anti-spoofing techniques would be required.

## Current Status

The project currently provides an end-to-end local attendance workflow:

```text
Registration → Face Capture → Training → Recognition → Attendance → Reports
```

Automated tests are included and the project is connected to GitHub with GitHub Actions CI.

## Future Improvements

Potential future improvements include:

* Stronger anti-spoofing / presentation-attack detection
* Recognition accuracy benchmarking
* Better camera/device error handling
* Role-based administration
* More detailed analytics
* Docker deployment
* Improved documentation and architecture diagrams
* Expanded automated test coverage
* Production deployment configuration

## License

License information can be added when the project is ready for a specific open-source license.
