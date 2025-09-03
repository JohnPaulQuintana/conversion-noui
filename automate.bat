@echo off
cd /d "%~dp0"

:: Ensure consistent logging
set LOGFILE=%~dp0logs\run_%DATE:~-4%-%DATE:~4,2%-%DATE:~7,2%_%TIME:~0,2%-%TIME:~3,2%.log
if not exist "%~dp0logs" mkdir "%~dp0logs"

:: Check if env exists, if not, create it
if not exist env (
    echo Creating virtual environment... >> "%LOGFILE%" 2>&1
    python -m venv env >> "%LOGFILE%" 2>&1
)

:: Activate virtual environment
echo Activating virtual environment... >> "%LOGFILE%" 2>&1
call env\Scripts\activate.bat >> "%LOGFILE%" 2>&1

:: Install requirements (only if needed)
if exist requirements.txt (
    echo Installing dependencies... >> "%LOGFILE%" 2>&1
    pip install -r requirements.txt >> "%LOGFILE%" 2>&1
)

:: Install Playwright (only first time)
if not exist "%USERPROFILE%\AppData\Local\ms-playwright" (
    echo Installing Playwright... >> "%LOGFILE%" 2>&1
    playwright install >> "%LOGFILE%" 2>&1
)

:: Run main.py
echo Running main.py... >> "%LOGFILE%" 2>&1
python main.py >> "%LOGFILE%" 2>&1

:: Deactivate virtual environment
call deactivate >> "%LOGFILE%" 2>&1

exit /b 0
