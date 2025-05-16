from app import db

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False) 
    transcription = db.Column(db.Text, nullable=True)  
    description = db.Column(db.Text, nullable=True)
    images = db.Column(db.PickleType, nullable=True) 

    def __repr__(self):
        return f'<UploadedFile {self.filename}>'