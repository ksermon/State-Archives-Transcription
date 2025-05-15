# Run script to perform OCR on a given image using the TROCR engine.

from app.utils.ocr_engine import run_ocr_engine
import os

# Configurable
image_path = "test_data/pages/page_12.png"
output_path = "test_data/ocr_output/page_12.txt"

# Run OCR
print(f"[INFO] Running OCR on {image_path}")
text = run_ocr_engine(image_path)

# Save result
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(text)

print(f"[INFO] Saved OCR output to {output_path}")
