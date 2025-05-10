import os
from flask import render_template, request, redirect, flash, url_for, abort
from werkzeug.utils import secure_filename
from app.main import bp
from app import db
from app.models import UploadedFile
from config import Config
from base64 import b64encode


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


@bp.route("/", methods=["GET"])
def file_list():
    # Display the main page with a list of uploaded files
    files = UploadedFile.query.all()
    return render_template("file_list.html", files=files)


@bp.route("/upload", methods=["GET", "POST"])
def file_upload():
    if request.method == "GET":
        # Render the file upload page for GET requests
        return render_template("file_upload.html")
    # Handle file upload and save to the database
    if "file" not in request.files:
        flash("No file part in the request.")
        return redirect(url_for("main.file_list"))
    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.")
        return redirect(url_for("main.file_list"))
    if file and allowed_file(file.filename):
        file_name = secure_filename(file.filename)
        file_content = file.read()  # Read the binary content of the file

        # TODO: Generate the transcription
        file_transcription = "placeholder"  # Placeholder for transcription logic

        # Save file info and content to the database
        db_file = UploadedFile(
            name=file_name, content=file_content, transcription=file_transcription
        )
        db.session.add(db_file)
        db.session.commit()

        flash(f'File "{file_name}" uploaded successfully!')
        return redirect(url_for("main.file_view", name=file_name))
    else:
        flash("Invalid file type.")
        return redirect(url_for("main.file_list"))


@bp.route("/view/<name>", methods=["GET"])
def file_view(name):
    # Retrieve file details and transcription from the database
    uploaded_file = UploadedFile.query.filter_by(name=name).first()
    if not uploaded_file:
        abort(404)  # File not found
    return render_template(
        "file_view.html",
        name=uploaded_file.name,
        content=b64encode(uploaded_file.content).decode("utf-8"),
        transcription=uploaded_file.transcription,
    )


@bp.route("/herosection")
def herosection():
    return render_template('herosection.html')

@bp.route("/list")
def list():
    return render_template('FileList.html')

@bp.route('/viewer')
def viewer():
    return render_template('FileView.html')

@bp.route('/up')
def up():
    return render_template('upload.html')