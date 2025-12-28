@echo off
title AutoPM V6 Launcher
echo ==========================================
echo      AutoPM V6 - Automotive Project Tool
echo ==========================================
echo.
echo [1/2] Checking and installing dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Could not install dependencies. 
    echo Please make sure Python is installed.
    echo.
    pause
    exit /b
)

echo.
echo [2/2] Launching Application...
echo.
streamlit run app.py

pause
