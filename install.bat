@echo off
pip show virtualenv >nul 2>&1 || pip install virtualenv

virtualenv venv
call venv\Scripts\activate
pip install -r requirements.txt
echo Setup complete. Activate your environment with "venv\Scripts\activate" and run "python run.py".
pause
