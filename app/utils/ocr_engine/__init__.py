from .ocr_model import load_model, recognize_single_image, recognize_batch_images
from .slicer import auto_slice_lines
from .preprocessing import preprocess_image
from .aggregator import aggregate_text
from PIL import Image

# def run_ocr_engine(image_path):
#     image = Image.open(image_path)
#     # preprocessing
#     preprocessed = preprocess_image(image)
    
#     # slicing
#     line_imgs = auto_slice_lines(preprocessed)
    
#     # line text
#     lines = [recognize_single_image(line_img) for line_img in line_imgs]
#     final_text = aggregate_text(lines)
#     return final_text
# def run_ocr_engine(image_path):
#     image = Image.open(image_path)

#     # Preprocess and slice
#     preprocessed = preprocess_image(image)
#     line_imgs = auto_slice_lines(preprocessed)

#     # Load model once
#     load_model()

#     # OCR per line using preloaded model
#     lines = []
#     # for line_img in line_imgs:
#     #     text = recognize_single_image(line_img)
#     #     lines.append(text)
    
#     lines = recognize_batch_images(line_imgs)

#     return aggregate_text(lines)

# Tried to optimize the model loading
def run_ocr_engine(image_path, processor, model):
    image = Image.open(image_path)
    preprocessed = preprocess_image(image)
    line_imgs = auto_slice_lines(preprocessed)
    lines = recognize_batch_images(line_imgs, processor, model)
    return aggregate_text(lines)
