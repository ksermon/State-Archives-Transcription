#!/bin/bash

if ! command -v virtualenv &> /dev/null
then
    echo "virtualenv not found. Installing virtualenv..."
    pip install virtualenv
fi

virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Setup complete. Activate your environment with 'source venv/bin/activate' and run 'flask run' or 'python run.py'."