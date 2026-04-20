@echo off
echo ========================================
echo  Trade Data AI Analyzer (Electron)
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please create a .env file with your OPENAI_API_KEY.
    echo You can copy .env.example to .env and add your API key.
    echo.
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules\" (
    echo Node modules not found. Please run setup_venv.bat first.
    echo.
    pause
    exit /b 1
)

echo Starting Trade Data AI Analyzer...
echo.
echo - Flask backend will start on http://127.0.0.1:5000
echo - Electron window will open automatically
echo.

call npm start

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo Application exited with an error.
    pause
)
