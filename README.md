# State-Archives-Transcription
## Prerequisites

- Python 3.8+ installed
- Git installed
- [pip](https://pip.pypa.io/en/stable/installation/)
- [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) (optional but recommended)

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/ksermon/State-Archives-Transcription.git
cd State-Archives-Transcription
```

### 2.1 Docker Deployment

1. Download Docker Desktop. 
2. Use `docker compose up` to run the server. 

It will automatically download any necessary dependencies, and will take longer the first time. 

### 2.2 Manual Deployment

After cloning the repository, for quick first time deployment:

**- On Linux/Mac:**
```bash
chmod +x setup.sh
./install.sh
```

**- On Windows:**
Open Command Prompt (or PowerShell) in the repository directory and run:
```
install.bat
```

To complete the deployment manually instead:

#### Create and activate a virtual environment
**- On Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**- On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

#### Install dependencies
```bash
pip install -r requirements.txt
```

#### Local Model Setup ####
This project is using `microsoft/trocr-base-handwritten` model.

Step-by-step Instructions
1. Create the model directory:
```bash
mkdir -p app/models/trocr-base-handwritten-local
```
2. Download the following files from Hugging Face:
- config.json
- preprocessor_config.json
- pytorch_model.bin

Place all three files into the folder:

```bash
app/models/trocr-base-handwritten-local/
```
Optional: Use Hugging Face CLI (if available)
If you have transformers-cli installed:

```bash
transformers-cli download microsoft/trocr-base-handwritten
```
Then manually move the downloaded files to:

```bash
app/models/trocr-base-handwritten-local/
```
**Directory Structure Example**
```
State-Archives-Transcription/
├── app/
│   └── models/
│       └── trocr-base-handwritten-local/
│           ├── config.json
│           ├── preprocessor_config.json
│           └── pytorch_model.bin
```

#### Set environment variables and run application

**- On Linux/Mac:**
```bash
export FLASK_APP=app.py
export FLASK_ENV=development  # Optional: enables debug mode
flask run
```

**- On Windows (CMD):**
```bash
set FLASK_APP=app.py
set FLASK_ENV=development  # Optional: enables debug mode
flask run
```

**- On Windows (PowerShell):**
```PowerShell
$env:FLASK_APP = "run.py"
$env:FLASK_ENV = "development"  # Optional: enables debug mode
flask run
```

#### Setting up DB

```bash
flask shell
from app import db
db.create_all()
exit()
```

The app can now be opened at http://127.0.0.1:5000/.

#### Quick Start (Subsequent Runs)

Follow these steps after the initial setup:

**Linux/macOS**
1. Open a terminal and navigate to the project root.
2. Activate your virtual environment with:
   ```bash
   source venv/bin/activate
   ```
3. Start the server using:
   ```bash
   flask run
   ```
4. Open your browser at `http://127.0.0.1:5000`.

**Windows**
1. Open Command Prompt or PowerShell and navigate to the project root.
2. Activate your virtual environment with:
   ```batch
   venv\Scripts\activate
   ```
3. Start the server using:
   ```batch
   flask run
   ```
4. Open your browser at `http://127.0.0.1:5000`.


## Production Deployment
Leaving this link here for deployment options later:
https://flask.palletsprojects.com/en/stable/deploying/
