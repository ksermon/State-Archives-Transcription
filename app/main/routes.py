import os
from flask import render_template, request, redirect, flash,url_for
from werkzeug.utils import secure_filename
from app.main import bp
from config import Config
from app.utils.ocr_engine import run_ocr_engine


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@bp.route('/', methods=['GET', 'POST'])
def index():
    transcribed_text = ""
    image_url = None  
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
            if filename.lower().endswith(('png', 'jpg', 'jpeg', 'gif', 'bmp')):
                 image_url = url_for('static', filename=f'uploads/{filename}')
            # TODO: Integrate  HCR transcription here.
            # TRocr recognition engine
            transcribed_text = run_ocr_engine(file_path)
            # transcribed_text = "Testing TextTesting TextTesting TextTesting TextTesting Text"
    return render_template('index.html', transcribed_text=transcribed_text,image_url=image_url)

