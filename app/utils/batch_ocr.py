# Gets the OCR text from the images
import os
import gc
import torch
from glob import glob
from multiprocessing import Pool, cpu_count, set_start_method
from app.utils.ocr_engine import run_ocr_engine
from app.utils.ocr_engine.ocr_model import load_model

INPUT_DIR = "test_data/pages"
OUTPUT_DIR = "test_data/ocr_output_2"
image_paths = sorted(glob(os.path.join(INPUT_DIR, "*.png")))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_single_image(image_path):
    print(f"[INFO] Processing: {image_path}")

    processor, model = load_model()
    text = run_ocr_engine(image_path, processor, model)

    output_file = os.path.join(OUTPUT_DIR, os.path.basename(image_path).replace(".png", ".txt"))
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    # Clean up
    del processor, model, text
    gc.collect()
    torch.cuda.empty_cache()

    return output_file

if __name__ == "__main__":
    # Important for Windows to avoid hanging
    set_start_method("spawn", force=True)

    # Dont use all avaliable cores, leave 2 for system(OS)
    usable_cores = cpu_count() - 2
    print(f"[INFO] Starting batch OCR using {usable_cores} cores...")

    with Pool(usable_cores) as pool:
        results = pool.map(process_single_image, image_paths)

    print(f"[INFO] Finished OCR on {len(results)} pages.")
