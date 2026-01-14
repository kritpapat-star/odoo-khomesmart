@echo off
REM ============================================
REM Batch script สำหรับรันการซิงค์และ Auto Features
REM ============================================

cd /d "%~dp0"

echo ======================================
echo ZK50-ODOO Sync Tool
echo Running at: %date% %time%
echo ======================================

REM ตรวจสอบ argument
if "%1"=="--auto-checkout" (
    echo Running Auto Check-Out...
    python app_secure.py --auto-checkout >> sync_output.log 2>&1
) else if "%1"=="--auto-checkin" (
    echo Running Auto Check-In...
    python app_secure.py --auto-checkin >> sync_output.log 2>&1
) else (
    echo Running Normal Sync...
    python app_secure.py >> sync_output.log 2>&1
)

echo Completed at: %date% %time%
echo ======================================
