@echo off
where pip >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo pip not found. Please install pip before proceeding.
    exit /B 1
)
where virtualenv >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo virtualenv not found. Installing virtualenv...
    pip install virtualenv
)
virtualenv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Setup complete. Activate your environment with "venv\Scripts\activate" and run "python run.py".
pause