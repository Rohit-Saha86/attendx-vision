(function () {
    "use strict";

    const STORAGE_KEY = "attendx-theme";

    // ==============================
    // Get saved theme
    // ==============================
    function getSavedTheme() {
        return localStorage.getItem(STORAGE_KEY) || "dark";
    }

    // ==============================
    // Apply theme
    // ==============================
    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);

        const button = document.querySelector(".theme-toggle");

        if (button) {
            button.textContent = theme === "dark" ? "☀" : "☾";
            button.setAttribute(
                "title",
                theme === "dark"
                    ? "Switch to Light Mode"
                    : "Switch to Dark Mode"
            );
        }
    }

    // ==============================
    // Create theme button
    // ==============================
    function createThemeButton() {
        if (document.querySelector(".theme-toggle")) {
            return;
        }

        const button = document.createElement("button");

        button.className = "theme-toggle";
        button.type = "button";
        button.setAttribute("aria-label", "Toggle theme");

        button.addEventListener("click", function () {
            const currentTheme =
                document.documentElement.getAttribute("data-theme") || "dark";

            const newTheme =
                currentTheme === "dark" ? "light" : "dark";

            localStorage.setItem(STORAGE_KEY, newTheme);
            applyTheme(newTheme);
        });

        document.body.appendChild(button);

        applyTheme(getSavedTheme());
    }

    // ==============================
    // Global Theme CSS
    // ==============================
    function addThemeStyles() {
        if (document.getElementById("attendx-theme-styles")) {
            return;
        }

        const style = document.createElement("style");

        style.id = "attendx-theme-styles";

        style.textContent = `

        /* =========================================
           GLOBAL
        ========================================= */

        html,
        body {
            transition:
                background-color 0.25s ease,
                color 0.25s ease;
        }

        body {
            transition:
                background-color 0.25s ease,
                color 0.25s ease;
        }

        /* =========================================
           THEME BUTTON
        ========================================= */

        .theme-toggle {
            position: fixed;
            right: 24px;
            bottom: 24px;

            width: 46px;
            height: 46px;

            border-radius: 50%;
            border: 1px solid #30363d;

            background: #161b22;
            color: #ffffff;

            display: flex;
            align-items: center;
            justify-content: center;

            font-size: 20px;
            cursor: pointer;

            z-index: 99999;

            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);

            transition:
                background 0.25s ease,
                color 0.25s ease,
                border-color 0.25s ease,
                transform 0.2s ease;
        }

        .theme-toggle:hover {
            transform: scale(1.08);
        }

        /* =========================================
           LIGHT MODE - BODY
        ========================================= */

        html[data-theme="light"] body {
            background: #f5f7fa !important;
            color: #1f2937 !important;
        }

        /* =========================================
           LIGHT MODE - NAVBAR
        ========================================= */

        html[data-theme="light"] nav,
        html[data-theme="light"] .navbar,
        html[data-theme="light"] .topbar {
            background: #ffffff !important;
            color: #1f2937 !important;
            border-color: #e5e7eb !important;
        }

        html[data-theme="light"] nav a,
        html[data-theme="light"] .navbar a {
            color: #374151 !important;
        }

        html[data-theme="light"] nav a:hover,
        html[data-theme="light"] .navbar a:hover {
            color: #111827 !important;
        }

        /* =========================================
           LIGHT MODE - CARDS
        ========================================= */

        html[data-theme="light"] .card,
        html[data-theme="light"] .stat-card,
        html[data-theme="light"] .info-card,
        html[data-theme="light"] .attendance-card,
        html[data-theme="light"] .profile-card,
        html[data-theme="light"] .history-card,
        html[data-theme="light"] .login-card {
            background: #ffffff !important;
            color: #1f2937 !important;
            border-color: #e5e7eb !important;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.06) !important;
        }

        /* =========================================
           LIGHT MODE - TEXT
        ========================================= */

        html[data-theme="light"] h1,
        html[data-theme="light"] h2,
        html[data-theme="light"] h3,
        html[data-theme="light"] h4,
        html[data-theme="light"] h5,
        html[data-theme="light"] h6 {
            color: #111827 !important;
        }

        html[data-theme="light"] p {
            color: #4b5563 !important;
        }

        html[data-theme="light"] .muted,
        html[data-theme="light"] .subtitle,
        html[data-theme="light"] .description {
            color: #6b7280 !important;
        }

        /* =========================================
           LIGHT MODE - INPUTS
        ========================================= */

        html[data-theme="light"] input,
        html[data-theme="light"] select,
        html[data-theme="light"] textarea {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: #d1d5db !important;
        }

        html[data-theme="light"] input::placeholder,
        html[data-theme="light"] textarea::placeholder {
            color: #9ca3af !important;
        }

        html[data-theme="light"] label {
            color: #374151 !important;
        }

        /* =========================================
           STUDENT LOGIN PAGE
        ========================================= */

        html[data-theme="light"] .login-card {
            background: #ffffff !important;
            color: #1f2937 !important;
            border-color: #e5e7eb !important;

            box-shadow:
                0 10px 30px rgba(0, 0, 0, 0.08) !important;
        }

        html[data-theme="light"] .login-card .logo {
            color: #111827 !important;
        }

        html[data-theme="light"] .login-card .logo-icon {
            background: #111827 !important;
            color: #ffffff !important;
        }

        html[data-theme="light"] .login-card .subtitle {
            color: #6b7280 !important;
        }

        html[data-theme="light"] .login-card .description {
            color: #6b7280 !important;
        }

        html[data-theme="light"] .login-card .form-group label {
            color: #374151 !important;
        }

        html[data-theme="light"] .login-card input {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: #d1d5db !important;
        }

        html[data-theme="light"] .login-card input::placeholder {
            color: #9ca3af !important;
        }

        html[data-theme="light"] .login-card .password-box {
            background: #ffffff !important;
        }

        html[data-theme="light"] .login-card .show-password {
            color: #6b7280 !important;
        }

        html[data-theme="light"] .login-card .register {
            color: #6b7280 !important;
        }

        html[data-theme="light"] .login-card .home-link {
            color: #374151 !important;
        }

        /* =========================================
           LIGHT MODE - BUTTONS
        ========================================= */

        html[data-theme="light"] button:not(.theme-toggle),
        html[data-theme="light"] .button {
            transition:
                background 0.25s ease,
                color 0.25s ease,
                border-color 0.25s ease;
        }

        /* =========================================
           LIGHT MODE - TABLE
        ========================================= */

        html[data-theme="light"] table {
            background: #ffffff !important;
            color: #1f2937 !important;
        }

        html[data-theme="light"] th {
            background: #f3f4f6 !important;
            color: #374151 !important;
        }

        html[data-theme="light"] td {
            color: #4b5563 !important;
            border-color: #e5e7eb !important;
        }

        /* =========================================
           LIGHT MODE - DROPDOWN
        ========================================= */

        html[data-theme="light"] select {
            background: #ffffff !important;
            color: #111827 !important;
        }

        /* =========================================
           LIGHT MODE - LOGIN FLASH
        ========================================= */

        html[data-theme="light"] .flash {
            border-color: #d1d5db !important;
        }

        /* =========================================
           LIGHT MODE - THEME BUTTON
        ========================================= */

        html[data-theme="light"] .theme-toggle {
            background: #ffffff !important;
            color: #111827 !important;
            border-color: #d1d5db !important;

            box-shadow:
                0 6px 18px rgba(0, 0, 0, 0.12);
        }

        /* =========================================
           DARK MODE - THEME BUTTON
        ========================================= */

        html[data-theme="dark"] .theme-toggle {
            background: #161b22;
            color: #ffffff;
            border-color: #30363d;
        }

        `;

        document.head.appendChild(style);
    }

    // ==============================
    // Initialize
    // ==============================
    function initializeTheme() {
        addThemeStyles();

        const savedTheme = getSavedTheme();

        document.documentElement.setAttribute(
            "data-theme",
            savedTheme
        );

        if (document.body) {
            createThemeButton();
        }
    }

    // Run after DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initializeTheme
        );
    } else {
        initializeTheme();
    }

})();