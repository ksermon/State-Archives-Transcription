import os

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

db = SQLAlchemy()

def _load_env():
    # Prefer all-users config written by installer:
    programdata_env = r"C:\ProgramData\StateArchivesTranscription\.env"
    if os.path.exists(programdata_env):
        load_dotenv(programdata_env, override=True)
    else:
        # Dev fallback: .env in project folder if present
        load_dotenv(override=False)

def create_app(config_class=Config):
    _load_env()
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config["USE_GEMINI"] = os.getenv("USE_GEMINI", "false").lower() == "true"
    app.config["GOOGLE_AI_API_KEY"] = os.getenv("GOOGLE_AI_API_KEY", "")

    db.init_app(app)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    return app

