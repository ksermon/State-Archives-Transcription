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
from app.utils.text_regions import extract_line_boxes, get_image_dimensions


def _align_boxes_to_lines(boxes, line_count):
    """
    Returns exactly 'line_count' boxes in reading order (top-to-bottom),
    padding with None when needed and truncating when there are too many.
    """
    if line_count <= 0:
        return []
    boxes = boxes or []
    boxes = sorted(boxes, key=lambda b: (b.get("y", 0), b.get("x", 0)))
    if len(boxes) >= line_count:
        return boxes[:line_count]
    return boxes + [None] * (line_count - len(boxes))

load_dotenv()
import uuid

# Dictionary to store upload progress (in production, use Redis or similar)
upload_progress = {}

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
        try:
            file_name = secure_filename(file.filename)
            file_content = file.read()
            images = pdf_to_images_base64(file_content)
            custom_name = request.form.get("name") or file_name
            description = request.form.get("description", "")
            upload_id = request.form.get("upload_id", str(uuid.uuid4()))

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
    pages = FilePage.query.filter_by(file_id=uploaded_file.id).order_by(FilePage.page_number).all()
    total_pages = len(pages)
    page = int(request.args.get('page', 1))
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
    if page < 1 or page > total_pages:
        page = 1

    current_page = pages[page - 1]
    image_base64 = base64.b64encode(current_page.image).decode("utf-8")
    transcription = current_page.transcription or "No transcription available."

    transcription_lines = transcription.splitlines() or [transcription]

    # Detect boxes
    detected_boxes = extract_line_boxes(current_page.image)

    # If detection is weak (too few boxes), synthesize evenly spaced ones
    if not detected_boxes or len(detected_boxes) < max(3, len(transcription_lines) // 2):
        from app.utils.text_regions import synthesize_line_boxes
        detected_boxes = synthesize_line_boxes(len(transcription_lines))

    # Align to exactly the number of transcription lines
    line_boxes = _align_boxes_to_lines(detected_boxes, len(transcription_lines))

    dimensions = get_image_dimensions(current_page.image)

    return render_template(
        "FileView.html",
        file_id=uploaded_file.id,
        name=uploaded_file.name,
        description=uploaded_file.description or "No description available.",
        image=image_base64,
        transcription=transcription,
        page=page,
        total_pages=total_pages,
        processing=False
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
