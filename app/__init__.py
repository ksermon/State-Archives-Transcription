import os
import re
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    


    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Register Blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    @app.template_filter('markdown_bold_to_html')
    def markdown_bold_to_html(s):
        if not s:
            return ""
        s = str(s)
        return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)

    return app
