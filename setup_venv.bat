@echo off
echo ========================================
echo  Installing Node.js Dependencies
echo ========================================
echo.

REM Check if Node.js is installed
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Node.js is not installed!
    echo.
    echo Please install Node.js from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo Installing NPM packages...
call npm install

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ERROR: Failed to install NPM packages
    pause
    exit /b 1
)

echo.
echo Installing Python dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   npm start
echo.
pause
