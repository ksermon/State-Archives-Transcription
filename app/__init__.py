import os
from flask import Flask
from regex import T
from app.config import Config
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    app.config.from_pyfile('config.py', silent=True)
    
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
