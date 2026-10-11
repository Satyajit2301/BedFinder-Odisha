@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   BedFinder Odisha v2.2 - One-Command Offline Run
echo ===================================================
echo.

rem Check python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not found in PATH. Please install Python 3.12+ and add to PATH.
    pause
    exit /b 1
)

echo [1/4] Checking enriched hospital dataset...
if not exist "data\hospitals_enriched.csv" (
    echo [INFO] Generating enriched dataset...
    python scripts\enrich_data.py
) else (
    echo [OK] data\hospitals_enriched.csv is present.
)

echo.
echo [2/4] Checking simulated hourly occupancy history...
if not exist "data\history.csv" (
    echo [INFO] Generating anchored history...
    python scripts\generate_history.py
) else (
    echo [OK] data\history.csv is present.
)

echo.
echo [3/4] Checking ML model bundle...
if not exist "models\bed_model.joblib" (
    echo [INFO] Training ML model...
    python scripts\train.py
) else (
    echo [OK] models\bed_model.joblib is present.
)

echo.
echo [4/4] Starting Streamlit web application...
echo ---------------------------------------------------
echo Point your browser to http://localhost:8501
echo ---------------------------------------------------
streamlit run app.py
