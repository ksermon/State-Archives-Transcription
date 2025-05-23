import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app','static','uploads')
    # Allowed file extensions for PDF uploads
    ALLOWED_EXTENSIONS = {'pdf'}

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(INSTANCE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable event notifications