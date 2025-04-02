from .ocr_model import recognize_single_image
from .slicer import auto_slice_lines
from .preprocessing import preprocess_image
from .aggregator import aggregate_text
from PIL import Image

def run_ocr_engine(image_path):
    image = Image.open(image_path)
    # preprocessing
    preprocessed = preprocess_image(image)
    
    # slicing
    line_imgs = auto_slice_lines(preprocessed)
    
    # line text
    lines = [recognize_single_image(line_img) for line_img in line_imgs]
    final_text = aggregate_text(lines)
    return final_text