@echo off
where pip >nul 2>&1 || (echo pip is required & exit /B 1)
where virtualenv >nul 2>&1 || pip install virtualenv

virtualenv venv
call venv\Scripts\activate
pip install -r requirements.txt

flask run