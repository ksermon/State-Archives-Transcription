import os
from flask import render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from app.main import bp
from config import Config

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET', 'POST'])
def index():
    transcribed_text = ""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected.')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
            # Make sure the upload folder exists
            os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
            file.save(file_path)
            # TODO: Integrate  HCR transcription here.
            transcribed_text = "[Transcribed text will appear here]."
    return render_template('index.html', transcribed_text=transcribed_text)