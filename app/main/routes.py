import os
from flask import render_template, request, redirect, flash, url_for, abort, session, jsonify
from werkzeug.utils import secure_filename
from app.main import bp
from app import db
from app.models import UploadedFile
from config import Config
from .utils import pdf_to_images_base64
from app.utils.ocr_engine import run_ocr_engine
import base64
from app.models import UploadedFile, FilePage
from dotenv import load_dotenv
from app.utils.gemini_transcriber import transcribe_images_with_gemini
from app.utils.text_regions import (
    extract_line_boxes_aligned,  # column/spread aware, aligned to line_count
    get_image_dimensions,
)

# ------------------------
# Helpers
# ------------------------

def _align_boxes_to_lines(boxes, line_count):
    """
    Returns exactly 'line_count' boxes in reading order (top-to-bottom, then left).
    Pads with None when needed and truncates when there are too many.
    """
    if line_count <= 0:
        return []
    boxes = boxes or []
    # Boxes from extract_line_boxes_aligned are already in reading order, but sort defensively
    try:
        boxes = sorted(boxes, key=lambda b: (b.get("x", 0), b.get("y", 0)))
    except Exception:
        # If any items are None or malformed, filter first
        boxes = [b for b in boxes if isinstance(b, dict)]
        boxes = sorted(boxes, key=lambda b: (b.get("x", 0), b.get("y", 0)))

    if len(boxes) >= line_count:
        return boxes[:line_count]
    return boxes + [None] * (line_count - len(boxes))


def _normalize_transcription_lines(text: str) -> list[str]:
    """
    Normalize line endings and expand tabs/spaces, preserving intentionally blank lines.
    Keeps user-visible spacing minimal without changing line count.
    """
    if not text:
        return [""]
    # Normalize line endings
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    # Replace tabs with single spaces to avoid layout explosions
    t = t.replace("\t", " ")
    # Split without keeping newline chars; preserves empty lines between content
    lines = t.split("\n")
    # Trim trailing spaces only, keep internal spacing
    return [ln.rstrip() for ln in lines]


load_dotenv()
import uuid

# Dictionary to store upload progress (in production, use Redis or similar)
upload_progress = {}

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )

# ------------------------
# Routes
# ------------------------

@bp.route("/", methods=["GET"])
def startpage():
    return render_template("herosection.html")


@bp.route("/list", methods=["GET"])
def file_list():
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


@bp.route("/upload", methods=["GET", "POST"])
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
        try:
            file_name = secure_filename(file.filename)
            file_content = file.read()
            images = pdf_to_images_base64(file_content)
            custom_name = request.form.get("name") or file_name
            description = request.form.get("description", "")
            upload_id = request.form.get("upload_id", str(uuid.uuid4()))

        # Mark uncertain characters
        mark_uncertainty = "mark_uncertainty" in request.form
            # Store total page count for this upload
            total_pages = len(images)
            upload_progress[upload_id] = {
                'total': total_pages,
                'processed': 0,
                'file_id': None
            }

        # Save the file record first
        db_file = UploadedFile(
            name=custom_name,
            content=file_content,
            description=description
        )
        db.session.add(db_file)
        db.session.commit()

        # Branch logic based on the selected transcription method
        if transcription_method == "gemini":
            batch_size = 10
            for i in range(0, len(images), batch_size):
                batch_images = images[i:i + batch_size]
                transcriptions = transcribe_images_with_gemini(
                    batch_images,
                    mark_uncertainty=mark_uncertainty
                )
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
        else:  # Default to 'trocr'
            # Save the file record first
            db_file = UploadedFile(
                name=custom_name,
                content=file_content,
                description=description
            )
            db.session.add(db_file)
            db.session.commit() 
            
            upload_progress[upload_id]['file_id'] = db_file.id

            # For each image, run OCR and save as FilePage
            print(f"Number of images: {total_pages}")
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
                db.session.commit()  # Commit each page for real-time updates
                
                # Update progress
                upload_progress[upload_id]['processed'] = idx + 1
                print(f"Page {idx + 1}/{total_pages} processed")

            # Clean up progress tracking after completion
            if upload_id in upload_progress:
                del upload_progress[upload_id]

            return jsonify({
                'success': True,
                'file_id': db_file.id,
                'redirect_url': url_for("main.file_view", file_id=db_file.id)
            })
        except Exception as e:
            import traceback
            print("Upload error:", traceback.format_exc())
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Invalid file type'}), 400

# Endpoint to check upload progress
@bp.route("/upload_progress/<upload_id>", methods=["GET"])
def upload_progress_status(upload_id):
    if upload_id in upload_progress:
        progress = upload_progress[upload_id]
        return jsonify({
            'total': progress['total'],
            'processed': progress['processed'],
            'file_id': progress['file_id']
        })
    else:
        return jsonify({'error': 'Upload not found'}), 404

# Endpoint to check processing status
@bp.route("/file_processing_status/<int:file_id>", methods=["GET"])
def file_processing_status(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file:
        return jsonify({'error': 'File not found'}), 404
    
    # Count how many pages have been processed
    processed_pages = FilePage.query.filter_by(file_id=file_id).count()
    # Try to get the total from upload_progress if available
    for progress in upload_progress.values():
        if progress.get('file_id') == file_id:
            total_pages = progress['total']
            break
    else:
        # Fallback: parse PDF
        from .utils import pdf_to_images_base64
        try:
            images = pdf_to_images_base64(uploaded_file.content)
            total_pages = len(images)
        except:
            total_pages = processed_pages if processed_pages > 0 else 1
    return jsonify({
        'total': total_pages,
        'processed': processed_pages,
        'file_id': file_id
    })


@bp.route("/view/<int:file_id>", methods=["GET"])
def file_view(file_id):
    uploaded_file = UploadedFile.query.get(file_id)
    if not uploaded_file:
        abort(404)

    # Get all pages for this file, ordered by page_number
    pages = (
        FilePage.query
        .filter_by(file_id=uploaded_file.id)
        .order_by(FilePage.page_number)
        .all()
    )
    total_pages = len(pages)
    if total_pages == 0:
        # No pages saved; show a minimal view
        flash("No pages found for this file.")
        return redirect(url_for("main.file_list"))

    # Page parameter (1-based)
    try:
        page = int(request.args.get("page", 1))
    if total_pages == 0:
        # No pages processed yet
        return render_template(
            "FileView.html",
            file_id=uploaded_file.id,
            name=uploaded_file.name,
            description=uploaded_file.description or "No description available.",
            image=None,
            transcription=None,
            page=1,
            total_pages=0,
            processing=True
        )
    except (TypeError, ValueError):
        page = 1
    if page < 1 or page > total_pages:
        page = 1

    current_page = pages[page - 1]
    image_base64 = base64.b64encode(current_page.image).decode("utf-8")
    transcription = current_page.transcription or "No transcription available."

    # 1) Normalize server-side line array (source of truth for UI and boxes)
    transcription_lines = _normalize_transcription_lines(transcription)

    # 2) Generate boxes aligned to the line count (auto column/spread aware)
    detected_boxes = extract_line_boxes_aligned(current_page.image, len(transcription_lines))

    # 3) Force exact length (safety)
    line_boxes = _align_boxes_to_lines(detected_boxes, len(transcription_lines))

    # 4) Dimensions for aspect ratio
    dimensions = get_image_dimensions(current_page.image)

    return render_template(
        "FileView.html",
        file_id=uploaded_file.id,
        name=uploaded_file.name,
        description=uploaded_file.description or "No description available.",
        image=image_base64,
        transcription="\n".join(transcription_lines),  # keep textarea consistent with lines shown
        page=page,
        total_pages=total_pages,
        processing=False
    )
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
        FilePage.query
        .filter_by(file_id=file_id)
        .order_by(FilePage.page_number)
        .all()
    )

    combined_text = "\n\n".join((page.transcription or "").strip() for page in pages)

    filename = f"{secure_filename(uploaded_file.name.rsplit('.', 1)[0]) or 'transcription'}.txt"
    response = Response(combined_text, mimetype="text/plain")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


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
            (UploadedFile.name.ilike(f"%{query}%"))
            | (UploadedFile.description.ilike(f"%{query}%"))
            | (FilePage.transcription.ilike(f"%{query}%"))
        )
        .distinct()
        .all()
    )

    if not search_results:
        flash("No files matched your search.")

    return render_template("SearchResults.html", files=search_results, query=query)
