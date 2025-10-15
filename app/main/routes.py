from flask import (
    render_template,
    request,
    redirect,
    flash,
    url_for,
    abort,
    jsonify,
    Response,
    send_file,
)
from werkzeug.utils import secure_filename
from app.main import bp
from app import db
from config import Config
from .utils import pdf_to_images_base64
from app.utils.ocr_engine import run_ocr_engine
import base64
from app.models import UploadedFile, FilePage
from dotenv import load_dotenv
from app.utils.gemini_transcriber import transcribe_images_with_gemini
from app.utils.text_regions import extract_line_boxes, get_image_dimensions
from io import BytesIO


def _align_boxes_to_lines(boxes, line_count):
    if line_count <= 0:
        return []
    boxes = boxes or []
    boxes = boxes[:line_count]
    if len(boxes) < line_count:
        boxes.extend([None] * (line_count - len(boxes)))
    return boxes

load_dotenv()

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
        # Get the selected transcription method from the form
        transcription_method = request.form.get("transcription_method", "trocr")

        # Mark unceratin characters
        mark_uncertainty = "mark_uncertainty" in request.form 

        # Save the file record first
        db_file = UploadedFile(
            name=custom_name,
            content=file_content,
            description=description
        )
        db.session.add(db_file)
        db.session.commit()

        # Branch logic based on the selected transcription method
        print(transcription_method)
        if transcription_method == "gemini":
            batch_size = 10
            for i in range(0, len(images), batch_size):
                batch_images = images[i:i + batch_size]
                transcriptions = transcribe_images_with_gemini(batch_images,mark_uncertainty=mark_uncertainty )

                for idx, (img_base64, transcription_text) in enumerate(zip(batch_images, transcriptions)):
                    page_number = i + idx + 1
                    img_bytes = base64.b64decode(img_base64)
                    db_page = FilePage(
                        file_id=db_file.id,
                        page_number=page_number,
                        image=img_bytes,
                        transcription=transcription_text
                    )
                    db.session.add(db_page)
        else: # Default to 'trocr'
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
        
        db.session.commit()

        flash(f'File "{file_name}" uploaded and transcribed using {transcription_method.upper()}!')
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

    transcription_lines = transcription.splitlines() or [transcription]
    line_boxes = extract_line_boxes(current_page.image)
    line_boxes = _align_boxes_to_lines(line_boxes, len(transcription_lines))
    dimensions = get_image_dimensions(current_page.image)

    return render_template(
        "FileView.html",
        file_id=uploaded_file.id,
        name=uploaded_file.name,
        description=uploaded_file.description or "No description available.",
        image=image_base64,
        transcription=transcription,
        transcription_lines=transcription_lines,
        line_boxes=line_boxes,
        image_dimensions=dimensions,
        page=page,
        total_pages=total_pages,
    )


@bp.route("/api/files/<int:file_id>/pages/<int:page>/transcription", methods=["PUT"])
def update_transcription(file_id, page):
    page_obj = FilePage.query.filter_by(file_id=file_id, page_number=page).first()
    if not page_obj:
        abort(404)

    data = request.get_json(silent=True) or {}
    new_text = data.get("transcription", "")
    page_obj.transcription = new_text
    db.session.commit()

    return jsonify({"status": "ok"})


@bp.route("/download/<int:file_id>/transcription", methods=["GET"])
def download_transcription(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file:
        abort(404)

    pages = (
        FilePage.query.filter_by(file_id=file_id)
        .order_by(FilePage.page_number)
        .all()
    )

    combined_text = "\n\n".join((page.transcription or "").strip() for page in pages)

    filename = f"{secure_filename(uploaded_file.name.rsplit('.', 1)[0]) or 'transcription'}.txt"
    response = Response(combined_text, mimetype="text/plain")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@bp.route("/api/files/<int:file_id>/pdf", methods=["GET"])
def stream_file_pdf(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file or not uploaded_file.content:
        abort(404)

    pdf_stream = BytesIO(uploaded_file.content)
    download_name = uploaded_file.name or f"file-{file_id}.pdf"

    return send_file(
        pdf_stream,
        mimetype="application/pdf",
        as_attachment=False,
        download_name=download_name,
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
