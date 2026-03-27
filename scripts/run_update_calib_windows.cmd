@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_PATH=%SCRIPT_DIR%update_calib_windows.ps1"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_PATH=%%~fI"

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%" -RepoPath "%REPO_PATH%" %*
set "EXIT_CODE=%ERRORLEVEL%"

echo.

if "%EXIT_CODE%"=="0" (
    powershell -NoProfile -Command "Write-Host 'Calibration save finished successfully.' -ForegroundColor Green"
    echo Press any key to close...
    pause >nul
) else (
    echo.
    echo Calibration save failed with exit code %EXIT_CODE%.
    echo Press any key to close...
    pause >nul
)

exit /b %EXIT_CODE%
