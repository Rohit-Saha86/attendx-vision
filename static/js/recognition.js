import {
    FaceLandmarker,
    FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/vision_bundle.mjs";


// ==========================================
// ELEMENTS
// ==========================================

const webcam = document.getElementById("webcam");
const faceMeshCanvas = document.getElementById("faceMeshCanvas");

const scanner = document.getElementById("scanner");
const scanRing = document.getElementById("scanRing");
const scanIcon = document.getElementById("scanIcon");
const scannerMessage = document.getElementById("scannerMessage");

const startCameraButton = document.getElementById("startCamera");
const stopCameraButton = document.getElementById("stopCamera");

const livenessIndicator = document.getElementById("livenessIndicator");

const successCard = document.getElementById("successCard");
const recognitionOverlay =
    document.getElementById("recognitionOverlay");

const recognitionOverlayName =
    document.getElementById("recognitionOverlayName");

const recognitionOverlayStatus =
    document.getElementById("recognitionOverlayStatus");
const welcomeName = document.getElementById("welcomeName");
const attendanceStatus = document.getElementById("attendanceStatus");
const attendanceCounter = document.getElementById("attendanceCounter");
const streakValue = document.getElementById("streakValue");

const failureCard = document.getElementById("failureCard");
const failureMessage = document.getElementById("failureMessage");
const retryButton = document.getElementById("retryButton");

const scanQueue = document.getElementById("scanQueue");
const queueCount = document.getElementById("queueCount");

const flaggedAttempts = document.getElementById("flaggedAttempts");
const flaggedCount = document.getElementById("flaggedCount");

const lightBoost = document.getElementById("lightBoost");
const multiScanToggle = document.getElementById("multiScanToggle");

const systemStatus = document.getElementById("systemStatus");

const greetingText = document.getElementById("greetingText");
const greetingTime = document.getElementById(
    "greetingTime"
);
const greetingSubtext = document.getElementById("greetingSubtext");


// ==========================================
// STATE
// ==========================================

let faceLandmarker = null;
let cameraStream = null;
let animationFrame = null;

let cameraRunning = false;
let modelReady = false;

let currentFaceDetected = false;
let livenessPassed = false;

let blinkDetected = false;
let smileDetected = false;

let lastVideoTime = -1;

let consecutiveFailures = 0;
let totalScans = 0;

let scanLocked = false;
let multiScanEnabled =
    getNumber("multi_scan_enabled", 0) === 1;

let noFaceTimer = null;

const NO_FACE_TIMEOUT = 15000;


// ==========================================
// LOCAL STORAGE
// ==========================================

function getNumber(key, defaultValue) {
    const value = localStorage.getItem(key);

    if (value === null) {
        return defaultValue;
    }

    const number = Number(value);

    if (Number.isNaN(number)) {
        return defaultValue;
    }

    return number;
}


function saveNumber(key, value) {
    localStorage.setItem(key, String(value));
}

async function loadStatistics(studentId = "") {

    try {

        const countResponse = await fetch(
            "/attendance-count",
            {
                cache: "no-store"
            }
        );

        if (!countResponse.ok) {
            throw new Error("Attendance count request failed");
        }

        const countData =
            await countResponse.json();

        totalScans =
            Number(countData.count) || 0;


        let streak = 0;

        if (studentId) {

            const streakResponse =
                await fetch(
                    "/attendance-streak?student_id=" +
                    encodeURIComponent(studentId),
                    {
                        cache: "no-store"
                    }
                );

            if (!streakResponse.ok) {
                throw new Error(
                    "Attendance streak request failed"
                );
            }

            const streakData =
                await streakResponse.json();

            streak =
                Number(streakData.streak) || 0;
        }


        if (attendanceCounter) {
            attendanceCounter.textContent =
                String(totalScans);
        }

        if (streakValue) {
            streakValue.textContent =
                String(streak);
        }

        updateFlaggedCount();

    } catch (error) {

        console.error(
            "Statistics error:",
            error
        );
    }
}



function updateFlaggedCount() {
    const count =
        getNumber("flagged_attempts", 0);

    if (flaggedCount) {
        flaggedCount.textContent =
            String(count);
    }
}


function recordFlaggedAttempt() {
    const count =
        getNumber("flagged_attempts", 0) + 1;

    saveNumber(
        "flagged_attempts",
        count
    );

    updateFlaggedCount();

    if (flaggedAttempts) {
        flaggedAttempts.classList.remove("hidden");
    }
}


// ==========================================
// GREETING
// ==========================================
function updateGreeting() {

    const hour =
        new Date().getHours();

    let greeting =
        "Welcome";

    let message =
        "Ready for attendance?";

    if (hour >= 5 && hour < 12) {

        greeting =
            "Good morning";

        message =
            "Ready for attendance?";

    } else if (hour >= 12 && hour < 17) {

        greeting =
            "Good afternoon";

        message =
            "Ready for your check-in?";

    } else if (hour >= 17 && hour < 22) {

        greeting =
            "Good evening";

        message =
            "Ready for attendance?";

    } else {

        greeting =
            "Good night";

        message =
            "Ready for a secure check-in?";
    }

    if (greetingTime) {

        greetingTime.textContent =
            greeting;
    }

    if (greetingText) {

        greetingText.textContent =
            message;
    }

    if (greetingSubtext) {

        greetingSubtext.textContent =
            "Look into the camera and complete the liveness action.";
    }
}


// ==========================================
// SYSTEM STATUS
// ==========================================

function setSystemStatus(text, state) {
    if (!systemStatus) {
        return;
    }

    systemStatus.textContent = text;

    systemStatus.classList.remove(
        "scanning",
        "success",
        "error"
    );

    if (state) {
        systemStatus.classList.add(state);
    }
}


// ==========================================
// LIVENESS
// ==========================================

function setLiveness(valid) {
    if (!livenessIndicator) {
        return;
    }

    if (valid) {
        livenessIndicator.classList.add(
            "liveness-valid"
        );

        livenessIndicator.innerHTML =
            '<span></span> Liveness confirmed';

    } else {
        livenessIndicator.classList.remove(
            "liveness-valid"
        );

        livenessIndicator.innerHTML =
            '<span></span> Liveness: Waiting';
    }
}


// ==========================================
// CAMERA
// ==========================================

async function startCamera() {
    if (cameraRunning) {
        return;
    }

    try {
        setSystemStatus(
            "STARTING",
            "scanning"
        );

        scannerMessage.textContent =
            "Requesting camera...";

        cameraStream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    width: {
                        ideal: 1280
                    },
                    height: {
                        ideal: 720
                    },
                    facingMode: "user"
                },
                audio: false
            });

        webcam.srcObject = cameraStream;

        await webcam.play();

        cameraRunning = true;

        if (startCameraButton) {
            startCameraButton.disabled = true;
        }

        if (stopCameraButton) {
            stopCameraButton.disabled = false;
        }

        setSystemStatus(
            "SCANNING",
            "scanning"
        );

        scannerMessage.innerHTML =
            '<span class="pulse-dot"></span> Searching for face...';

        setLiveness(false);

        renderLoop();

    } catch (error) {
        console.error(
            "Camera error:",
            error
        );

        setSystemStatus(
            "CAMERA ERROR",
            "error"
        );

        scannerMessage.textContent =
            "Camera permission was not granted.";

        showFailure(
            "Camera access was not available. Please allow camera access and try again."
        );
    }
}


function stopCamera() {
    cameraRunning = false;

    if (animationFrame) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }

    if (cameraStream) {
        cameraStream
            .getTracks()
            .forEach(function(track) {
                track.stop();
            });

        cameraStream = null;
    }

    if (webcam) {
        webcam.srcObject = null;
    }

    setSystemStatus(
        "READY",
        ""
    );

    scannerMessage.textContent =
        "Scanner stopped.";

    setLiveness(false);

    if (startCameraButton) {
        startCameraButton.disabled = false;
    }

    if (stopCameraButton) {
        stopCameraButton.disabled = true;
    }
}


// ==========================================
// MEDIAPIPE
// ==========================================

async function initializeFaceLandmarker() {
    try {
        setSystemStatus(
            "INITIALIZING",
            "scanning"
        );

        scannerMessage.textContent =
            "Loading face detection model...";

        const vision =
            await FilesetResolver.forVisionTasks(
                "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm"
            );

        faceLandmarker =
            await FaceLandmarker.createFromOptions(
                vision,
                {
                    baseOptions: {
                        modelAssetPath:
                            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
                    },

                    runningMode: "VIDEO",

                    numFaces: 2,

                    minFaceDetectionConfidence: 0.5,

                    minFacePresenceConfidence: 0.5,

                    minTrackingConfidence: 0.5,

                    outputFaceBlendshapes: true,

                    outputFacialTransformationMatrixes: false
                }
            );

        modelReady = true;

        setSystemStatus(
            "READY",
            ""
        );

        scannerMessage.textContent =
            "Face detector ready.";

    } catch (error) {
        console.error(
            "Face model error:",
            error
        );

        modelReady = false;

        setSystemStatus(
            "MODEL ERROR",
            "error"
        );

        scannerMessage.textContent =
            "Unable to load face detection model.";
    }
}


// ==========================================
// CANVAS
// ==========================================

function prepareCanvas() {
    if (!webcam || !faceMeshCanvas) {
        return;
    }

    if (
        webcam.videoWidth === 0 ||
        webcam.videoHeight === 0
    ) {
        return;
    }

    if (
        faceMeshCanvas.width !== webcam.videoWidth ||
        faceMeshCanvas.height !== webcam.videoHeight
    ) {
        faceMeshCanvas.width =
            webcam.videoWidth;

        faceMeshCanvas.height =
            webcam.videoHeight;
    }
}


function clearCanvas() {
    if (!faceMeshCanvas) {
        return;
    }

    const ctx =
        faceMeshCanvas.getContext("2d");

    ctx.clearRect(
        0,
        0,
        faceMeshCanvas.width,
        faceMeshCanvas.height
    );
}


// ==========================================
// FACE MESH
// ==========================================

function drawFaceMesh(landmarks) {
    if (!faceMeshCanvas) {
        return;
    }

    const ctx =
        faceMeshCanvas.getContext("2d");

    ctx.clearRect(
        0,
        0,
        faceMeshCanvas.width,
        faceMeshCanvas.height
    );

    if (!landmarks || landmarks.length === 0) {
        return;
    }

    const points = landmarks;

    const importantPoints = [
        10,
        152,
        33,
        133,
        362,
        263,
        61,
        291,
        1,
        168,
        6,
        94,
        0
    ];

    ctx.lineWidth = 1.2;
    ctx.strokeStyle =
        "rgba(0, 220, 255, 0.65)";

    ctx.fillStyle =
        "rgba(0, 220, 255, 0.9)";

    importantPoints.forEach(
        function(index) {
            const point = points[index];

            if (!point) {
                return;
            }

            const x =
                point.x *
                faceMeshCanvas.width;

            const y =
                point.y *
                faceMeshCanvas.height;

            ctx.beginPath();

            ctx.arc(
                x,
                y,
                2.5,
                0,
                Math.PI * 2
            );

            ctx.fill();
        }
    );

    const connections = [
        [10, 338],
        [338, 297],
        [297, 332],
        [332, 284],
        [284, 251],
        [251, 389],
        [389, 356],
        [356, 454],
        [454, 323],
        [323, 361],
        [361, 288],
        [288, 397],
        [397, 365],
        [365, 379],
        [379, 378],
        [378, 400],
        [400, 377],
        [377, 152],

        [10, 109],
        [109, 67],
        [67, 103],
        [103, 54],
        [54, 21],
        [21, 162],
        [162, 127],
        [127, 234],
        [234, 93],
        [93, 132],
        [132, 58],
        [58, 172],
        [172, 136],
        [136, 150],
        [150, 149],
        [149, 176],
        [176, 148],
        [148, 152]
    ];

    connections.forEach(
        function(connection) {
            const first =
                points[connection[0]];

            const second =
                points[connection[1]];

            if (!first || !second) {
                return;
            }

            ctx.beginPath();

            ctx.moveTo(
                first.x *
                    faceMeshCanvas.width,
                first.y *
                    faceMeshCanvas.height
            );

            ctx.lineTo(
                second.x *
                    faceMeshCanvas.width,
                second.y *
                    faceMeshCanvas.height
            );

            ctx.stroke();
        }
    );
}


// ==========================================
// BLINK / SMILE
// ==========================================

function getBlendshapeScore(
    categories,
    name
) {
    if (!categories) {
        return 0;
    }

    for (
        let i = 0;
        i < categories.length;
        i += 1
    ) {
        if (
            categories[i].categoryName === name
        ) {
            return categories[i].score;
        }
    }

    return 0;
}


function analyzeBlendshapes(result) {
    blinkDetected = false;
    smileDetected = false;

    if (
        !result.faceBlendshapes ||
        result.faceBlendshapes.length === 0
    ) {
        return;
    }

    const categories =
        result.faceBlendshapes[0].categories;

    const leftBlink =
        getBlendshapeScore(
            categories,
            "eyeBlinkLeft"
        );

    const rightBlink =
        getBlendshapeScore(
            categories,
            "eyeBlinkRight"
        );

    const smileLeft =
        getBlendshapeScore(
            categories,
            "mouthSmileLeft"
        );

    const smileRight =
        getBlendshapeScore(
            categories,
            "mouthSmileRight"
        );

    if (
        leftBlink > 0.45 ||
        rightBlink > 0.45
    ) {
        blinkDetected = true;
    }

    if (
        smileLeft > 0.45 &&
        smileRight > 0.45
    ) {
        smileDetected = true;
    }

    if (
        blinkDetected ||
        smileDetected
    ) {
        livenessPassed = true;
        setLiveness(true);
    }
}


// ==========================================
// FACE DETECTION
// ==========================================

function processFaceResult(result) {
    const hasFace =
        result &&
        result.faceLandmarks &&
        result.faceLandmarks.length > 0;

    currentFaceDetected =
        hasFace;

    if (!hasFace) {
    clearCanvas();

    livenessPassed = false;

    setLiveness(false);

    scannerMessage.innerHTML =
        '<span class="pulse-dot"></span> Searching for face...';


    // Start the no-face timer.
    // If nobody appears for 15 seconds,
    // stop the camera.

    if (
    !noFaceTimer &&
    cameraRunning
) {
    noFaceTimer = setTimeout(
        function() {

            noFaceTimer = null;

            if (scanner) {
                scanner.classList.add(
                    "camera-standby"
                );
            }

            if (scannerMessage) {
                scannerMessage.textContent =
                    "Waiting for student...";
            }

        },
        NO_FACE_TIMEOUT
    );
}

    return;
}


// A face is present again,
// so cancel the no-face timer.

if (noFaceTimer) {
    clearTimeout(noFaceTimer);
    noFaceTimer = null;
}

if (scanner) {
    scanner.classList.remove(
        "camera-standby"
    );
}

    const landmarks =
        result.faceLandmarks[0];

    drawFaceMesh(landmarks);

    analyzeBlendshapes(result);

    if (!livenessPassed) {
        scannerMessage.innerHTML =
            '<span class="pulse-dot"></span> Face detected - smile or blink';
    } else {
        scannerMessage.innerHTML =
            '<span class="pulse-dot"></span> Liveness verified';
    }

    if (
        livenessPassed &&
        !scanLocked
    ) {
        handleLivenessSuccess();
    }
}


// ==========================================
// SCAN SUCCESS
// ==========================================

function handleLivenessSuccess() {
    scanLocked = true;

    consecutiveFailures = 0;

    setLiveness(true);

    if (scannerMessage) {
        scannerMessage.innerHTML =
            '<span class="pulse-dot"></span> Liveness verified - waiting for identity...';
    }

    setTimeout(
        function() {
            scanLocked = false;
        },
        1000
    );
}


function showSuccess(name) {
    if (scanner) {
        scanner.classList.remove(
            "scanner-failure"
        );

        scanner.classList.add(
            "scanner-success"
        );
    }

    if (scanRing) {
        scanRing.classList.add(
            "success-ring"
        );
    }

    if (scanIcon) {
        scanIcon.textContent = "✓";
    }

    setSystemStatus(
        "VERIFIED",
        "success"
    );

    if (welcomeName) {
        welcomeName.textContent =
            "Welcome, " + name;
    }

    if (attendanceStatus) {
        attendanceStatus.textContent =
            "Liveness verified - identity check ready";
    }

    /*
     * This frontend success state does not write attendance
     * to MySQL. The actual identity/attendance verification
     * will be connected to the existing Python backend next.
     */

    if (successCard) {
        successCard.classList.remove(
            "hidden"
        );

        successCard.classList.add(
            "success-card-in"
        );
    }
    const recognitionOverlay =
    document.getElementById("recognitionOverlay");

    if (recognitionOverlay) {
        recognitionOverlay.classList.remove("show");
    }

    if (
        multiScanEnabled &&
        scanQueue
    ) {
        addQueueItem(name);
    }
}


// ==========================================
// FAILURE
// ==========================================

function showFailure(message) {
    consecutiveFailures += 1;

    if (failureMessage) {
        failureMessage.textContent =
            message;
    }

    if (failureCard) {
        failureCard.classList.remove(
            "hidden"
        );
    }

    if (scanner) {
        scanner.classList.add(
            "scanner-failure"
        );
    }

    setSystemStatus(
        "RETRY",
        "error"
    );

    if (
        consecutiveFailures >= 3
    ) {
        recordFlaggedAttempt();
    }
}


function hideFailure() {
    if (failureCard) {
        failureCard.classList.add(
            "hidden"
        );
    }

    if (scanner) {
        scanner.classList.remove(
            "scanner-failure"
        );
    }
}


// ==========================================
// QUEUE
// ==========================================

function addQueueItem(
    name,
    studentId = "",
    attendanceMarked = false
) {
    if (!scanQueue) {
        return;
    }

    const queueKey =
        studentId +
        "|" +
        name +
        "|" +
        attendanceMarked;

    // Prevent the exact same scan from being added twice in a row.
    const firstItem =
        scanQueue.querySelector(".queue-item");

    if (
        firstItem &&
        firstItem.dataset.queueKey === queueKey
    ) {
        return;
    }

    const emptyMessage =
        scanQueue.querySelector("p");

    if (emptyMessage) {
        emptyMessage.remove();
    }

    const item =
        document.createElement("div");

    item.className =
        "queue-item";

    item.dataset.queueKey =
        queueKey;

    const nameElement =
        document.createElement("div");

    nameElement.className =
        "font-semibold text-white";

    nameElement.textContent =
        name;

    const idElement =
        document.createElement("div");

    idElement.className =
        "text-xs text-slate-400";

    idElement.textContent =
        studentId;

    const statusElement =
        document.createElement("div");

    statusElement.className =
        "mt-1 text-xs text-emerald-300";

    statusElement.textContent =
        attendanceMarked
            ? "Attendance marked"
            : "Attendance already marked today";

    item.appendChild(nameElement);
    item.appendChild(idElement);
    item.appendChild(statusElement);

    scanQueue.prepend(item);

    const items =
        scanQueue.querySelectorAll(
            ".queue-item"
        );

    if (items.length > 10) {
        items[items.length - 1].remove();
    }

    if (queueCount) {
        queueCount.textContent =
            String(
                scanQueue.querySelectorAll(
                    ".queue-item"
                ).length
            );
    }
}


// ==========================================
// LOW LIGHT
// ==========================================

function detectLowLight() {
    if (!webcam || !webcam.videoWidth) {
        return;
    }

    const canvas =
        document.createElement("canvas");

    canvas.width = 32;
    canvas.height = 24;

    const ctx =
        canvas.getContext("2d");

    ctx.drawImage(
        webcam,
        0,
        0,
        32,
        24
    );

    const image =
        ctx.getImageData(
            0,
            0,
            32,
            24
        );

    let total = 0;

    for (
        let i = 0;
        i < image.data.length;
        i += 4
    ) {
        const r = image.data[i];
        const g = image.data[i + 1];
        const b = image.data[i + 2];

        total +=
            (r + g + b) / 3;
    }

    const average =
        total /
        (image.data.length / 4);

    if (average < 45) {
        if (lightBoost) {
            lightBoost.classList.add(
                "active"
            );
        }
    } else {
        if (lightBoost) {
            lightBoost.classList.remove(
                "active"
            );
        }
    }
}

let lastFrameSent = 0;

async function sendRecognitionFrame() {

    if (
        !webcam ||
        !webcam.videoWidth ||
        !webcam.videoHeight
    ) {
        return;
    }

    const now =
        Date.now();

    // Send at most one frame every 500 ms.
    if (
        now - lastFrameSent < 500
    ) {
        return;
    }

    lastFrameSent = now;

    const canvas =
        document.createElement(
            "canvas"
        );

    canvas.width =
        webcam.videoWidth;

    canvas.height =
        webcam.videoHeight;

    const context =
        canvas.getContext("2d");

    context.drawImage(
        webcam,
        0,
        0,
        canvas.width,
        canvas.height
    );

    canvas.toBlob(
        async function(blob) {

            if (!blob) {
                return;
            }

            try {

                const response = await fetch(
    "/recognition-frame",
    {
        method: "POST",
        headers: {
            "Content-Type":
                "image/jpeg"
        },
        body: blob
    }
);

const result = await response.json();

if (
    result.status === "recognized" &&
    result.recognition_sound
) {
    const audioContext =
        new (window.AudioContext ||
            window.webkitAudioContext)();

    const oscillator =
        audioContext.createOscillator();

    const gainNode =
        audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(
        0.15,
        audioContext.currentTime
    );

    oscillator.start();

    oscillator.stop(
        audioContext.currentTime + 0.15
    );
}

            } catch (error) {

                console.error(
                    "Frame upload error:",
                    error
                );

            }

        },
        "image/jpeg",
        0.75
    );
}

// ==========================================
// RENDER LOOP
// ==========================================

async function renderLoop() {
    if (!cameraRunning) {
        return;
    }

    if (
        !modelReady ||
        !faceLandmarker
    ) {
        animationFrame =
            requestAnimationFrame(
                renderLoop
            );

        return;
    }

    prepareCanvas();

    detectLowLight();

    if (
        webcam.readyState >=
        HTMLMediaElement.HAVE_CURRENT_DATA
    ) {
        const currentTime =
            webcam.currentTime;

        if (
            currentTime !== lastVideoTime
        ) {
            lastVideoTime =
                currentTime;

            try {
                const result =
                    faceLandmarker.detectForVideo(
                        webcam,
                        performance.now()
                    );

                processFaceResult(result);

                if (livenessPassed) {
                    sendRecognitionFrame();
                }
            } catch (error) {
                console.error(
                    "Face detection error:",
                    error
                );
            }
        }
    }

    animationFrame =
        requestAnimationFrame(
            renderLoop
        );
}


// ==========================================
// EVENTS
// ==========================================

if (startCameraButton) {
    startCameraButton.addEventListener(
        "click",
        async function() {
            hideFailure();

            await startCamera();
        }
    );
}


if (stopCameraButton) {
    stopCameraButton.addEventListener(
        "click",
        function() {
            stopCamera();
        }
    );
}
// Keyboard shortcut: press S to stop the camera
document.addEventListener(
    "keydown",
    function(event) {
        if (
            event.key.toLowerCase() === "s" &&
            !event.ctrlKey &&
            !event.altKey &&
            !event.metaKey
        ) {
            stopCamera();
        }
    }
);

if (retryButton) {
    retryButton.addEventListener(
        "click",
        function() {
            hideFailure();

            scanLocked = false;

            consecutiveFailures = 0;

            livenessPassed = false;

            setLiveness(false);

            setSystemStatus(
                "SCANNING",
                "scanning"
            );

            scannerMessage.innerHTML =
                '<span class="pulse-dot"></span> Searching for face...';
        }
    );
}


if (multiScanToggle) {

    multiScanToggle.setAttribute(
        "aria-pressed",
        String(multiScanEnabled)
    );

    multiScanToggle.addEventListener(
        "click",
        function() {

            multiScanEnabled =
                !multiScanEnabled;

            saveNumber(
                "multi_scan_enabled",
                multiScanEnabled ? 1 : 0
            );

            multiScanToggle.setAttribute(
                "aria-pressed",
                String(multiScanEnabled)
            );

        }
    );

}


// ==========================================
// INITIALIZATION
// ==========================================

updateGreeting();

loadStatistics();

setLiveness(false);

if (stopCameraButton) {
    stopCameraButton.disabled = true;
}

setSystemStatus(
    "INITIALIZING",
    "scanning"
);

initializeFaceLandmarker();
startCamera();

// ==========================================
// REAL PYTHON RECOGNITION STATUS
// ==========================================

let lastRecognitionStatus = "";

async function checkRecognitionStatus() {
    try {
        const response = await fetch(
            "/recognition-status",
            {
                cache: "no-store"
            }
        );

        if (!response.ok) {
            return;
        }

        const data = await response.json();

        const recognitionKey =
            data.status + "|" +
            data.student_id + "|" +
            data.name + "|" +
            data.attendance_marked;

        if (
            recognitionKey ===
            lastRecognitionStatus
        ) {
            return;
        }

        lastRecognitionStatus =
            recognitionKey;


        // ==========================================
        // REGISTERED STUDENT
        // ==========================================

        if (
            data.status === "recognized"
            && data.name
        ) {

            showRealRecognition(
                data.name,
                data.student_id,
                data.attendance_marked
            );

            return;
        }


        // ==========================================
        // UNKNOWN / UNREGISTERED STUDENT
        // ==========================================

        if (
            data.status === "unknown"
        ) {

            showUnknownRecognition();

            return;
        }

    } catch (error) {

        console.error(
            "Recognition status error:",
            error
        );
    }
}

function showUnknownRecognition() {

    scanLocked = true;


    if (scanner) {

        scanner.classList.remove(
            "scanner-success"
        );

        scanner.classList.add(
            "scanner-failure"
        );
    }


    if (scanRing) {

        scanRing.classList.remove(
            "success-ring"
        );
    }


    if (scanIcon) {
        scanIcon.textContent = "!";
    }


    setSystemStatus(
        "NOT MATCHED",
        "error"
    );


    // Big popup
    const overlay =
        document.getElementById(
            "recognitionOverlay"
        );

    const overlayName =
        document.getElementById(
            "recognitionOverlayName"
        );

    const overlayStatus =
        document.getElementById(
            "recognitionOverlayStatus"
        );

    const overlayIcon =
        overlay
            ? overlay.querySelector(
                ".recognition-overlay-icon"
            )
            : null;


    if (overlayName) {

        overlayName.textContent =
            "NOT MATCHED";
    }


    if (overlayStatus) {

        overlayStatus.textContent =
            "Unknown Student • Not Registered";
    }


    if (overlayIcon) {

        overlayIcon.textContent =
            "!";
    }


    if (overlay) {

        overlay.classList.add(
            "show",
            "unknown-result"
        );
    }


    if (scannerMessage) {

        scannerMessage.innerHTML =
            '<span class="pulse-dot"></span> ' +
            'Student not registered';
    }


    console.log(
        "Unknown student detected."
    );


    // IMPORTANT:
    // Do NOT call:
    // saveSuccessfulScan()
    // loadStatistics()
    // mark_attendance()
    //
    // Therefore this result does NOT
    // increase attendance.


    setTimeout(
        function() {

            scanLocked = false;

            livenessPassed = false;


            if (scanner) {

                scanner.classList.remove(
                    "scanner-success",
                    "scanner-failure"
                );
            }


            if (scanRing) {

                scanRing.classList.remove(
                    "success-ring"
                );
            }


            if (scanIcon) {

                scanIcon.textContent =
                    "✓";
            }


            if (overlay) {

                ooverlay.classList.remove(
                    "show",
                    "unknown-result"
                );
            }


            if (overlayIcon) {

                overlayIcon.textContent =
                    "✓";
            }


            setLiveness(false);


            setSystemStatus(
                "SCANNING",
                "scanning"
            );


            if (scannerMessage) {

                scannerMessage.innerHTML =
                    '<span class="pulse-dot"></span> ' +
                    'Searching for face...';
            }

        },
        3000
    );
}


function showRealRecognition(
    name,
    studentId,
    attendanceMarked
) {
    const recognitionOverlay =
        document.getElementById(
            "recognitionOverlay"
        );

    const recognitionOverlayName =
        document.getElementById(
            "recognitionOverlayName"
        );

    const recognitionOverlayStatus =
        document.getElementById(
            "recognitionOverlayStatus"
        );

    if (recognitionOverlayName) {
        recognitionOverlayName.textContent =
            "YOU ARE PRESENT";
    }

    if (recognitionOverlayStatus) {
        recognitionOverlayStatus.textContent =
            attendanceMarked
                ? "Welcome, " + name + " • Attendance marked successfully"
                : "Welcome, " + name + " • Attendance already marked today";
    }

    if (recognitionOverlay) {
        recognitionOverlay.classList.add("show");
    }
    scanLocked = true;

    const overlay =
        document.getElementById(
            "recognitionOverlay"
        );

    const overlayName =
        document.getElementById(
            "recognitionOverlayName"
        );

    const overlayStatus =
        document.getElementById(
            "recognitionOverlayStatus"
        );

    const overlayIcon =
        overlay
            ? overlay.querySelector(
                ".recognition-overlay-icon"
            )
            : null;

    // Scanner success state
    if (scanner) {
        scanner.classList.remove(
            "scanner-failure"
        );

        scanner.classList.add(
            "scanner-success"
        );
    }

    if (scanRing) {
        scanRing.classList.add(
            "success-ring"
        );
    }

    if (scanIcon) {
        scanIcon.textContent = "✓";
    }

    setSystemStatus(
        "VERIFIED",
        "success"
    );

    // Update success card
    if (welcomeName) {
        welcomeName.textContent =
            "Welcome, " + name;
    }

    if (attendanceStatus) {
        if (attendanceMarked) {
            attendanceStatus.textContent =
                "Attendance marked successfully";
        } else {
            attendanceStatus.textContent =
                "Attendance already marked today";
        }
    }

    if (successCard) {
        successCard.classList.remove(
            "hidden"
        );

        successCard.classList.add(
            "success-card-in"
        );
    }

    // Full success popup
    if (overlayName) {
        overlayName.textContent =
            "Welcome, " + name;
    }

    if (overlayStatus) {
        if (attendanceMarked) {
            overlayStatus.textContent =
                "Attendance marked successfully";
        } else {
            overlayStatus.textContent =
                "Attendance already marked today";
        }
    }

    if (overlayIcon) {
        overlayIcon.textContent = "✓";
    }

    if (overlay) {
        overlay.classList.add("show");
        overlay.classList.remove(
            "unknown-result"
        );
    }

    loadStatistics(studentId);

    console.log(
        "SUCCESS MARK SHOWN:",
        name,
        studentId,
        attendanceMarked
    );

    // Reset after 3 seconds
    setTimeout(
        function() {

            scanLocked = false;
            livenessPassed = false;

            if (scanner) {
                scanner.classList.remove(
                    "scanner-success",
                    "scanner-failure"
                );
            }

            if (scanRing) {
                scanRing.classList.remove(
                    "success-ring"
                );
            }

            if (scanIcon) {
                scanIcon.textContent = "✓";
            }

            if (successCard) {
                successCard.classList.remove(
                    "success-card-in"
                );

                successCard.classList.add(
                    "hidden"
                );
            }

            if (overlay) {
                overlay.classList.remove(
                    "show"
                );
            }

            setLiveness(false);

            setSystemStatus(
                "SCANNING",
                "scanning"
            );

            if (scannerMessage) {
                scannerMessage.innerHTML =
                    '<span class="pulse-dot"></span> Searching for face...';
            }

        },
        3000
    );
}

// Check the Python recognition result
// every 1 second.
setInterval(
    checkRecognitionStatus,
    1000
);

// ==========================================
// UNKNOWN STUDENT VISUAL STYLE
// ==========================================

(function () {

    const style =
        document.createElement("style");

    style.textContent = `
        #recognitionOverlay.unknown-result
        .recognition-overlay-icon {
            color: #fb7185 !important;
            border-color: #fb7185 !important;
            background: rgba(127, 29, 29, 0.18) !important;
            box-shadow:
                0 0 30px rgba(244, 63, 94, 0.35) !important;
        }

        #recognitionOverlay.unknown-result
        .recognition-overlay-name {
            color: #fb7185 !important;
        }

        #recognitionOverlay.unknown-result
        .recognition-overlay-status {
            color: #fecdd3 !important;
        }
    `;

    document.head.appendChild(style);

})();