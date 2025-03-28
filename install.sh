if ! command -v pip &> /dev/null; then
    echo "pip not found. Please install pip before proceeding."
    exit 1
fi
if ! command -v virtualenv &> /dev/null; then
    echo "virtualenv not found. Installing virtualenv..."
    pip install virtualenv
fi
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
echo "Setup complete. Activate your environment with 'source venv/bin/activate' and run 'python run.py'."
