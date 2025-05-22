from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from PIL import Image
import torch
from .preprocessing import preprocess_image


MODEL_PATH = "microsoft/trocr-base-handwritten"

def load_model():
    
    # global processor, model
    # if processor is None or model is None:
    #     processor = TrOCRProcessor.from_pretrained(MODEL_PATH)
    #     model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
    #     model.eval()

    processor = TrOCRProcessor.from_pretrained(MODEL_PATH)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
    model.eval()
    return processor, model

# def recognize_single_image(img : Image.Image)-> str:
def recognize_single_image(img: Image.Image, processor, model) -> str:
    # load_model()  
    # apply preprocessing
    # img = preprocess_image(img)
    
    with torch.no_grad():
        pixel_values = processor(images=img, return_tensors="pt").pixel_values
        generated_ids = model.generate(pixel_values)
        text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return text.strip()

def recognize_batch_images(images: list[Image.Image], processor, model) -> list[str]:
    with torch.no_grad():
        pixel_values = processor(images=images, return_tensors="pt", padding=True).pixel_values
        generated_ids = model.generate(pixel_values)
        return processor.batch_decode(generated_ids, skip_special_tokens=True)
