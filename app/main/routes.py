import os
from flask import render_template, request, redirect, flash, url_for, abort
from werkzeug.utils import secure_filename
from app.main import bp
from app import db
from app.models import UploadedFile
from config import Config
from base64 import b64encode
from .utils import pdf_to_images_base64
from app.utils.ocr_engine import run_ocr_engine


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


@bp.route("/upload", methods=["GET","POST"])
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
        images = pdf_to_images_base64(file_content) #Store images into database
        # Get custom name and decription
        custom_name = request.form.get("name") or file_name
        description = request.form.get("description", "")
        # TODO: Generate the transcription
        file_transcription = "placeholder"  # Placeholder for transcription logic
        # can use run_ocr_engine(filepath) on an image

        # Save file info and content to the database
        db_file = UploadedFile(
            name=custom_name, content=file_content, description=description,transcription=file_transcription,images=images
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

    return render_template("SearchResults.html", files=search_results, query=query)

@bp.route("/transcribe/<name>", methods=["GET","POST"])
def file_transcribe(name):

    # get uploaded file from database
    uploaded_file = UploadedFile.query.filter_by(name=name).first()
    if not uploaded_file:
        abort(404)  #

    # convert pdf into images
    images = uploaded_file.images
    
    total_pages = len(images)
    page = int(request.args.get('page', 1))
    if page < 1 or page > total_pages:
        page = 1

    image_to_show = images[page-1]
    return render_template("TranscribeView.html",
                           name=uploaded_file.name, 
                           image=image_to_show, 
                           images=images,
                           page=page, total_pages=total_pages,
                           content=b64encode(uploaded_file.content).decode("utf-8"),)