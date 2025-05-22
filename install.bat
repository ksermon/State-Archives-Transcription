@echo off
if exist venv rd /s /q venv
python -m venv venv
call venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m flask run
pause