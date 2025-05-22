import os
from flask import render_template, request, redirect, flash, url_for, abort
from werkzeug.utils import secure_filename
from app.main import bp
from app import db
from app.models import UploadedFile
from config import Config
from .utils import pdf_to_images_base64
from app.utils.ocr_engine import run_ocr_engine
import base64
from app.models import UploadedFile, FilePage


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

@bp.route("/delete/<int:file_id>", methods=["POST"])
def delete_file(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file:
        abort(404)
    # Delete all pages first
    FilePage.query.filter_by(file_id=file_id).delete()
    db.session.delete(uploaded_file)
    db.session.commit()
    flash("File deleted successfully.")
    return redirect(url_for("main.file_list"))

@bp.route("/upload", methods=["GET","POST"])
def file_upload():
    if request.method == "GET":
        return render_template("FileUpload.html")
    if "file" not in request.files:
        flash("No file part in the request.")
        return redirect(url_for("main.file_list"))
    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.")
        return redirect(url_for("main.file_list"))
    if file and allowed_file(file.filename):
        file_name = secure_filename(file.filename)
        file_content = file.read()
        images = pdf_to_images_base64(file_content)
        custom_name = request.form.get("name") or file_name
        description = request.form.get("description", "")

        # Save the file record first
        db_file = UploadedFile(
            name=custom_name,
            content=file_content,
            description=description
        )
        db.session.add(db_file)
        db.session.commit() 

        # For each image, run OCR and save as FilePage
        print(f"Number of images: {len(images)}")
        for idx, img_base64 in enumerate(images):
            transcription = run_ocr_engine(img_base64)
            img_bytes = base64.b64decode(img_base64)
            db_page = FilePage(
                file_id=db_file.id,
                page_number=idx + 1,
                image=img_bytes,
                transcription=transcription
            )
            db.session.add(db_page)
            print(f"Page {idx + 1} added with transcription: {transcription}")
        db.session.commit()

        flash(f'File "{file_name}" uploaded successfully!')
        return redirect(url_for("main.file_view", file_id=db_file.id))
    else:
        flash("Invalid file type.")
        return redirect(url_for("main.file_list"))


@bp.route("/view/<int:file_id>", methods=["GET"])
def file_view(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file:
        abort(404)

    # Get all pages for this file, ordered by page_number
    pages = FilePage.query.filter_by(file_id=uploaded_file.id).order_by(FilePage.page_number).all()
    total_pages = len(pages)
    page = int(request.args.get('page', 1))
    if page < 1 or page > total_pages:
        page = 1

    current_page = pages[page - 1]
    image_base64 = base64.b64encode(current_page.image).decode("utf-8")
    transcription = current_page.transcription or "No transcription available."

    return render_template(
        "FileView.html",
        file_id=uploaded_file.id,
        name=uploaded_file.name,
        description=uploaded_file.description or "No description available.",
        image=image_base64,
        transcription=transcription,
        page=page,
        total_pages=total_pages,
    )

@bp.route("/search", methods=["GET"])
def search_files():
    query = request.args.get("searchbar", "").strip()
    
    if not query:
        flash("Please enter a search term.")
        return redirect(url_for("main.file_list"))

    # Search UploadedFile name/description or any FilePage transcription
    search_results = (
        UploadedFile.query
        .outerjoin(FilePage, UploadedFile.id == FilePage.file_id)
        .filter(
            (UploadedFile.name.ilike(f"%{query}%")) |
            (UploadedFile.description.ilike(f"%{query}%")) |
            (FilePage.transcription.ilike(f"%{query}%"))
        )
        .distinct()
        .all()
    )

    if not search_results:
        flash("No files matched your search.")

    return render_template("SearchResults.html", files=search_results, query=query)
