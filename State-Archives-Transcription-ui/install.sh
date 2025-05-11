#!/bin/bash
command -v pip >/dev/null 2>&1 || { echo "pip is required"; exit 1; }
command -v virtualenv >/dev/null 2>&1 || pip install virtualenv

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt

flask run