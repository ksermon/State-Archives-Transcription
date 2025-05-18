from app import db

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    content = db.Column(db.LargeBinary, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<UploadedFile {self.name}>'

class FilePage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('uploaded_file.id'), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    image = db.Column(db.LargeBinary, nullable=False)  
    transcription = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<FilePage FileID={self.file_id} Page={self.page_number}>'