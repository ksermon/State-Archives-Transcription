# Take in pdf, convert to images, run OCR on each image, and save the text output

import os
from pdf2image import convert_from_path
from app.utils.ocr_engine import run_ocr_engine

def process_pdf(pdf_path, output_text=False, output_dir="test_data/ocr_output"):
    # Create folders if needed
    image_output_folder = "test_data/pages"
    os.makedirs(image_output_folder, exist_ok=True)
    if output_text:
        os.makedirs(output_dir, exist_ok=True)

    print("[INFO] Converting PDF to images...")
    pages = convert_from_path(pdf_path, dpi=300)

    all_text = ""
    for i, page in enumerate(pages):
        image_path = os.path.join(image_output_folder, f"page_{i+1}.png")
        page.save(image_path, "PNG")

        print(f"\n[INFO] Running OCR on {image_path}")
        text = run_ocr_engine(image_path)
        all_text += f"\n\n--- Page {i+1} ---\n\n{text}"

        if not output_text:
            print("OCR OUTPUT ")
            print(text)

    if output_text:
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        text_file_path = os.path.join(output_dir, f"{base_name}.txt")
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(all_text)
        print(f"[INFO] Saved combined OCR output to {text_file_path}")

if __name__ == "__main__":
    # Configurable
    pdf_path = "test_data/SROWA-series287-cons2826-item007.pdf"
    save_output_to_files = True  # Set to True to save as .txt files
    

    process_pdf(pdf_path, output_text=save_output_to_files)
