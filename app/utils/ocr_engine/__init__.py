from .ocr_model import load_model, recognize_single_image, recognize_batch_images
from .slicer import auto_slice_lines
from .preprocessing import preprocess_image
from .aggregator import aggregate_text
from PIL import Image
import io
import base64

# def run_ocr_engine(image_path, processor, model):
def run_ocr_engine(image_base64):
    image = Image.open(io.BytesIO(base64.b64decode(image_base64)))
    # image = Image.open(image_path)
    processor, model = load_model()
    
    # preprocessing
    preprocessed = preprocess_image(image)
    line_imgs = auto_slice_lines(preprocessed)
    
    # lines = recognize_batch_images(line_imgs, processor, model)
    lines = [recognize_single_image(line_img, processor, model) for line_img in line_imgs]
    
    final_text = aggregate_text(lines)
    return final_text
