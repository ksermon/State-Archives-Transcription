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
def startpage():
    return render_template("herosection.html")

@bp.route("/list", methods=["GET"])
def file_list():
    # Display the main page with a list of uploaded files
    files = UploadedFile.query.all()
    return render_template("FileList.html", files=files)


@bp.route("/upload", methods=["GET", "POST"])
def file_upload():
    if request.method == "GET":
        # Render the file upload page for GET requests
        return render_template("FileUpload.html")
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
        # Get custom name and decription
        custom_name = request.form.get("name") or file_name
        description = request.form.get("description", "")
        # TODO: Generate the transcription
        file_transcription = "placeholder"  # Placeholder for transcription logic

        # Save file info and content to the database
        db_file = UploadedFile(
            name=custom_name, content=file_content, description=description,transcription=file_transcription
        )
        db.session.add(db_file)
        db.session.commit()

        flash(f'File "{file_name}" uploaded successfully!')
        return redirect(url_for("main.file_view", name=custom_name))
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
        "FileView.html",
        name=uploaded_file.name,
        description = uploaded_file.description or "No description available.",
        content=b64encode(uploaded_file.content).decode("utf-8"),
        transcription=uploaded_file.transcription,
    )

@bp.route("/search", methods=["GET"])
def search_files():
    query = request.args.get("searchbar", "").strip()
    
    if not query:
        flash("Please enter a search term.")
        return redirect(url_for("main.file_list"))

    # search relevant text
    search_results = UploadedFile.query.filter(
        (UploadedFile.name.ilike(f"%{query}%")) |
        (UploadedFile.description.ilike(f"%{query}%")) |
        (UploadedFile.transcription.ilike(f"%{query}%"))
    ).all()

    if not search_results:
        flash("No files matched your search.")

    return render_template("search_results.html", files=search_results, query=query)
