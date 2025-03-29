import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app','static','uploads')
    # Allowed file extensions for image/PDF uploads
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    # Add additional configuration settings, e.g., SQLALCHEMY_DATABASE_URI for database connections